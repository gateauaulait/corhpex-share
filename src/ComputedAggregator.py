from .BaseAggregator import BaseAggregator
import re
import numpy as np
import os
import ply.lex as lex
import ply.yacc as yacc
import math

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class ComputedAggregator(BaseAggregator):
    """
    Aggregator to combine multiple aggregators

    Attributes:
        config (Configuration): the exploration configuration
        _store (dict of ()): Dictionnary to store metrics already read, inner aggregators should use the same
        aggregators: a list of aggregators
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_app_config_metric_stat(self, b, a, config):
        """
        Return the statistics for a pair of application and configuration

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute

        Returns:
            A list of dicts containing the lists of statistics labeled by metric.
            In the top level list, an item correspnds to a variant of the application.
            In the last level list, an item corresponds to a statistic ordered as in `stat_fn`
        """
        id_str = self.config.get_conf(config)

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            self.__store_app_config_metric(b, a, config)

            # Get the statistics for each metric
            for m in self.config.metrics["computed"]:
                values = self._store[entry_id][m["id"]]
                res_tmp[m["id"]] = [stat_fn[fn_id](values) for fn_id in self.config.res_stats]

            res.append(res_tmp)

        return res

    def get_app_config_metric(self, b, a, config):
        """
        Return the lists of metric metarepetitions for a pair of application and configuration

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute

        Returns:
            A list of one dict containing the target statistic wraped in a one item list for all
            the metrics collected labeled by metric
        """
        id_str = self.config.get_conf(config)

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            # Store metrics
            self.__store_app_config_metric(b, a, config)

            # Get the values for each metric
            for m in self.config.metrics["computed"]:
                res_tmp[m["id"]] = self._store[entry_id][m["id"]]

            res.append(res_tmp)

        return res

    def __store_app_config_metric(self, b, a, config):
        """
        Read metrics values and store them in _store

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        id_str = self.config.get_conf(config)

        res = []
        for i,v in enumerate(a["variants"]):
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            for m in self.config.metrics["computed"]:
                values = []
                res_tmp[m["id"]] = []
                for k in range(self.config.meta_rep):
                    calc = Calc()
                    for id_,vals in self._store[entry_id].items():
                        calc.eval(id_ + "=" + str(vals[k]))
                    expr = calc.eval(m["expr"])
                    values.append(expr)

                self._store[entry_id][m["id"]] = values

    def app_config_was_evaluated(self, b, a, config):
        """
        Return True only if the configuration was evaluated

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        return True

    def write_stats_to_csv(self, metric_id):
        """
        Write the statistics of a metric to a CSV file

        Args:
            metric_id (str): the identifier of the metric
        """
        for k,fn_id in enumerate(self.config.res_stats):
            res_id = 0
            with open(self.config.res_dir +'/' + metric_id + '_' + fn_id +'.csv', "w") as outputFile:

                storage = dict()
                headers = []
                for e,v in self._store.items():
                    if e[0] in storage:
                        storage[e[0]].append(stat_fn[fn_id](v[metric_id]))
                    else:
                        storage[e[0]] = []
                    if e[1] not in headers:
                        headers.append(e[1])

                # Write headers
                outputFile.write("apps")
                for h in headers:
                    outputFile.write("," + h)
                outputFile.write("\n")

                # Write values
                for a,v in storage.items():
                    outputFile.write(a)
                    for e in v:
                        outputFile.write(",{:.3f}".format(e))

    def add(self, aggreg):
        aggreg._store = self._store
        self.aggregators.append(aggreg)

    def get_metrics_ids(self):
        """
        Return:
            A list of strings that are metric ids
        """
        return [ m["id"] for m in self.config.metrics["computed"]]

# PARSER
class Parser:
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()

    def __init__(self, **kw):
        self.debug = kw.get('debug', 0)
        self.names = {}
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
        except:
            modname = "parser" + "_" + self.__class__.__name__
        self.debugfile = modname + ".dbg"
        # print self.debugfile

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile)

    def eval(self, expr):
        res = yacc.parse(expr)
        return res

class Calc(Parser):

    tokens = (
        'NAME', 'NUMBER',
        'PLUS', 'MINUS', 'EXP', 'TIMES', 'DIVIDE', 'EQUALS',
        'LPAREN', 'RPAREN',
    )

    # Tokens

    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_EXP = r'\*\*'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_EQUALS = r'='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'

    def t_NUMBER(self, t):
        r'([0-9]*[.])?[0-9]+([eE][-+]?[0-9]+)?'
        try:
            t.value = float(t.value)
        except ValueError:
            print("Integer value too large %s" % t.value)
            t.value = 0
        # print "parsed number %s" % repr(t.value)
        return t

    t_ignore = " \t"

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    # Parsing rules

    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE'),
        ('left', 'EXP'),
        ('right', 'UMINUS'),
    )

    def p_statement_assign(self, p):
        'statement : NAME EQUALS expression'
        self.names[p[1]] = p[3]

    def p_statement_expr(self, p):
        'statement : expression'
        # print(p[1])
        p[0] = p[1]

    def p_expression_binop(self, p):
        """
        expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression EXP expression
        """
        # print [repr(p[i]) for i in range(0,4)]
        if p[2] == '+':
            p[0] = p[1] + p[3]
        elif p[2] == '-':
            p[0] = p[1] - p[3]
        elif p[2] == '*':
            p[0] = p[1] * p[3]
        elif p[2] == '/':
            if p[3] == 0:
                p[0] = math.inf
            else:
                p[0] = p[1] / p[3]
        elif p[2] == '**':
            p[0] = p[1] ** p[3]

    def p_expression_uminus(self, p):
        'expression : MINUS expression %prec UMINUS'
        p[0] = -p[2]

    def p_expression_group(self, p):
        'expression : LPAREN expression RPAREN'
        p[0] = p[2]

    def p_expression_number(self, p):
        'expression : NUMBER'
        p[0] = p[1]

    def p_expression_name(self, p):
        'expression : NAME'
        try:
            p[0] = self.names[p[1]]
        except LookupError:
            print("Undefined name '%s'" % p[1])
            p[0] = 0

    def p_error(self, p):
        if p:
            print("Syntax error at '%s'" % p.value)
        else:
            print("Syntax error at EOF")
