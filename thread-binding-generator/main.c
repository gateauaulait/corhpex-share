#include <hwloc.h>

#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static bool tree_search(hwloc_topology_t topology, hwloc_obj_t obj, int depth);

/** Get the number of processing units contained in an object
 * @param obj the object to consider
 */
unsigned get_nb_pu(hwloc_obj_t obj) {
  unsigned count = 0;
  if (obj->arity) {
    return count + obj->arity * get_nb_pu(obj->first_child);
  }
  return 1;
}

/** Initialize the userdata fields in all nodes below an object
 * @param obj the object to consider
 */
void init_userdata(hwloc_obj_t obj) {
  obj->userdata = malloc(2 * sizeof(unsigned));
  *(unsigned *)obj->userdata = 0;
  *((unsigned *)obj->userdata + sizeof(unsigned)) = get_nb_pu(obj);
  for (int i = 0; i < obj->arity; i++) {
    init_userdata(obj->children[i]);
  }
}

/** Get the arity of the first descendent whose arity is not 1
 * @param obj the object to consider
 * @return if all descendent have an arity on 1 until the leaf return 1, else
 * return the arity of the first descendent whose arity is greater than 1
 * @note The aim of this function is to flatten the tree when several levels
 * have only one children
 */
unsigned get_descendent_arity(hwloc_obj_t obj) {
  hwloc_obj_t obj_exp = obj;
  while (obj_exp->first_child->arity <= 1) {
    if (obj_exp->first_child->arity == 0) {
      return 1;
    } else {
      obj_exp = obj_exp->first_child;
    }
  }
  return obj_exp->first_child->arity;
}

typedef struct {
  int package;
  int die;
  int numa;
  int l3;
  int smt;
} binding_policy_t;

/** Package, Die, Numa, L3, SMT */
binding_policy_t bp = {1, 1, 1, 1, 1};
/** The array containing the PUs in the specified binding order */
int *cores;
/** The index of the next value to set in the *cores* array */
int c = 0;

/** Apply the first policy where the PUs below an object are filled before going
 * to the next object of this level
 * @param topology the topology of the machine
 * @param obj the currently visited node
 * @param depth USELESS
 * @return true if the parent node can ask the next sibiling next time else
 * false
 */
static bool policy_first(hwloc_topology_t topology, hwloc_obj_t obj,
                         int depth) {

  // Decrement the number of visits left
  *((unsigned *)obj->userdata + sizeof(unsigned)) -= 1;

  // Ask the next child (index in userdata) to add the PU next index to the
  // binding list
  // If the child returns true then it should not be visited next time,
  // increment the next child index (in userdata)
  if (tree_search(topology, obj->children[*(unsigned *)obj->userdata], depth)) {
    (*(unsigned *)obj->userdata)++;
  }

  // Wrap the next child index when it reaches arity
  *(unsigned *)obj->userdata = (*(unsigned *)obj->userdata) % obj->arity;

  // When their are no visits left tell the parent to not ask again next time
  if (*((unsigned *)obj->userdata + sizeof(unsigned)) == 0) {
    return true;
  }

  // Tell the parent to ask again next time
  return false;
}

/** Apply the last policy where the PUs below the node must be filled with
 * lowest priority
 * @param topology the topology of the machine
 * @param obj the currently visited node
 * @param depth USELESS
 * @return true, the parent node can always ask the next sibiling next time
 */
static bool policy_last(hwloc_topology_t topology, hwloc_obj_t obj, int depth) {
  // Decrement the number of visits left
  *((unsigned *)obj->userdata + sizeof(unsigned)) -= 1;

  // Ask the next child (index in userdata) to add the PU next index to the
  // binding list
  // If the child returns true then it should not be visited next time,
  // increment the next child index (in userdata)
  if (tree_search(topology, obj->children[*(unsigned *)obj->userdata], depth)) {
    (*(unsigned *)obj->userdata)++;
  }

  // Wrap the next child index when it reaches arity
  *(unsigned *)obj->userdata = (*(unsigned *)obj->userdata) % obj->arity;

  // Tell the parent to not ask again next time
  return true;
}

/** Check is a PU is free
 * @param puidx the index of the PU whose availability we want to check
 * @return true if the PU is available, false is it is not */
static bool is_pu_free(int puidx) {
  // Look for puidx in cores
  for (int i = 0; i < c; i++) {
    if (cores[i] == puidx) {
      return false;
    }
  }
  return true;
}

/** The one ring to bind them all dispatch to the correct policy depending on
 * the type of the node
 * @param topology the topology of the machine
 * @param obj the currently visited node
 * @param depth USELESS
 * @return true if the parent node can ask the next sibiling next time else
 * false (just true if the search has gone well)
 */
static bool tree_search(hwloc_topology_t topology, hwloc_obj_t obj, int depth) {
  switch (obj->type) {
  case HWLOC_OBJ_PU:
    cores[c] = obj->logical_index;
    /* printf("------ Map thread to PU %d\n", obj->logical_index); */
    c += 1;
    return true;
  case HWLOC_OBJ_PACKAGE:
    if (bp.package) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  case HWLOC_OBJ_DIE:
    if (bp.die) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  case HWLOC_OBJ_L3CACHE:
    if (bp.l3) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  case HWLOC_OBJ_L2CACHE:
    if (bp.smt) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  case HWLOC_OBJ_L1CACHE:
    if (bp.smt) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  case HWLOC_OBJ_CORE:
    if (bp.smt) {
      return policy_first(topology, obj, 4);
    } else {
      return policy_last(topology, obj, 4);
    }
    break;
  default:
    return policy_first(topology, obj, depth);
  }

  return true;
}

int check_arg(char *sv) {
  int v = strtol(sv, NULL, 10);
  if (v == 0 || v == 1) {
    return v;
  } else {
    fprintf(stderr, "Error : Wrong value, must be 0 or 1, is %d\n", v);
    exit(1);
  }
}

int main(int argc, char **argv) {
  int topodepth;
  hwloc_topology_t topology;
  hwloc_obj_t obj;

  if (argc == 5) {
    bp.package = check_arg(argv[1]);
    bp.die = check_arg(argv[2]);
    bp.l3 = check_arg(argv[3]);
    bp.smt = check_arg(argv[4]);
  } else {
    fprintf(stderr, "Error : Wrong number of arguments, must be 4, is %d\n",
            argc - 1);
    exit(1);
  }

  /* Allocate and initialize topology object. */
  hwloc_topology_init(&topology);

  /* Perform the topology detection. */
  hwloc_topology_load(topology);

  /* Optionally, get some additional topology information
     in case we need the topology depth later. */
  topodepth = hwloc_topology_get_depth(topology);
  obj = hwloc_get_root_obj(topology);

  unsigned nb_pu = get_nb_pu(obj);
  cores = calloc(nb_pu, sizeof(int));

  init_userdata(obj);

  for (int i = 0; i < nb_pu; i++) {
    tree_search(topology, obj, 0);
  }

  for (int i = 0; i < nb_pu; i++) {
    printf("%u ", cores[i]);
  }
  printf("\n");
}
