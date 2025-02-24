#include <omp.h>
#include <omp-tools.h>
#include <stdio.h>
#include <likwid.h>

// defines the size of ids for parallel regions
#define SIZE_ID 15

static ompt_get_thread_data_t ompt_get_thread_data;
static ompt_get_unique_id_t ompt_get_unique_id;

static int init_profile = 0;
double ep_time_profiling_start = 0;

extern void study_energy_init(); 
extern void rapl_sysfs_start();
extern double rapl_sysfs_stop();

FILE *file;
FILE *file_En;

static void on_ompt_callback_parallel_begin(ompt_data_t *encountering_task_data,
	const ompt_frame_t *encountering_task_frame, ompt_data_t *parallel_data,
	uint32_t requested_parallelism, int flags, const void *codeptr_ra) {

	// init likwid and setup profiling
	if (init_profile == 0) {
		file = fopen("profile_simple.csv", "w");
		file_En = fopen("profile_simple_energy.csv", "w");
		init_profile = 1;
		//likwid_markerInit();	
		#pragma omp parallel
		{
			printf("parallelism init\n");  
			//likwid_markerThreadInit();
		}
	}
	char id[SIZE_ID];
	sprintf(id, "%d", *((int *)codeptr_ra));
	// likwid_markerStartRegion(id);
	// Temporary fix to enable one name for all parallel regions
	// TODO: to update per region id - will need to fix the aggregator
	//likwid_markerStartRegion("compute");
	ep_time_profiling_start = omp_get_wtime();
	rapl_sysfs_start();
}


static void on_ompt_callback_parallel_end(ompt_data_t *parallel_data,
                                          ompt_data_t *encountering_task_data,
                                          int flags, const void *codeptr_ra) {
	char id[SIZE_ID];
	sprintf(id, "%d", *((int *)codeptr_ra));
	//likwid_markerStopRegion(id);
	// TODO: temporary fix to profile the whole application
	double ep_time_profiling_end = omp_get_wtime();
	printf("\n[%p];%f\n", codeptr_ra,ep_time_profiling_end - ep_time_profiling_start);
	fprintf(file, "[%p];%f\n", codeptr_ra,ep_time_profiling_end - ep_time_profiling_start);

	double total_energy = rapl_sysfs_stop();
	printf("\n[%p];%f\n", codeptr_ra,total_energy);
	fprintf(file_En, "[%p];%f\n", codeptr_ra,total_energy);
	
	//likwid_markerStopRegion("compute");
}

#define register_callback_t(name, type)                                        \
  do {                                                                         \
    type f_##name = &on_##name;                                                \
    if (ompt_set_callback(name, (ompt_callback_t)f_##name) == ompt_set_never)  \
      printf("0: Could not register callback '" #name "'\n");                  \
  } while (0)

#define register_callback(name) register_callback_t(name, name##_t)

int ompt_initialize(ompt_function_lookup_t lookup, int initial_device_num,
                    ompt_data_t *tool_data) {
	printf("libomp init time: %f\n",
		 omp_get_wtime() - *(double *)(tool_data->ptr));
	*(double *)(tool_data->ptr) = omp_get_wtime();

	ompt_set_callback_t ompt_set_callback =
	  (ompt_set_callback_t)lookup("ompt_set_callback");
	ompt_get_thread_data = (ompt_get_thread_data_t)lookup("ompt_get_thread_data");
	ompt_get_unique_id = (ompt_get_unique_id_t)lookup("ompt_get_unique_id");

	register_callback(ompt_callback_parallel_begin);
	register_callback(ompt_callback_parallel_end);

	study_energy_init();
	
  return 1; // success: activates tool
}

void ompt_finalize(ompt_data_t *tool_data) {
	printf("application runtime: %f\n",
		 omp_get_wtime() - *(double *)(tool_data->ptr));
	//likwid_markerClose();
	fclose(file);
	fclose(file_En);
}

ompt_start_tool_result_t *ompt_start_tool(unsigned int omp_version,
                                          const char *runtime_version) {
	static double time = 0; // static defintion needs constant assigment
	time = omp_get_wtime();
	static ompt_start_tool_result_t ompt_start_tool_result = {
	  &ompt_initialize, &ompt_finalize, {.ptr = &time}};
	return &ompt_start_tool_result; // success: registers tool
}
