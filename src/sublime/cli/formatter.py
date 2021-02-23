# coding=utf-8
"""Output formatters."""

from __future__ import print_function

import re
import functools
import json
from xml.dom.minidom import parseString

import gron
import ansimarkup
import click
import colorama
from jinja2 import Environment, PackageLoader

JINJA2_ENV = Environment(loader=PackageLoader("sublime.cli"),
        extensions=['jinja2.ext.loopcontrols'])

colorama.init()
ANSI_MARKUP = ansimarkup.AnsiMarkup(
    tags={
        "header": ansimarkup.parse("<bold>"),
        "key": ansimarkup.parse("<cyan>"),
        "value": ansimarkup.parse("<green>"),
        "not-detected": ansimarkup.parse("<dim>"),
        "fail": ansimarkup.parse("<light-red>"),
        "success": ansimarkup.parse("<green>"),
        "unknown": ansimarkup.parse("<dim>"),
        "detected": ansimarkup.parse("<light-green>"),
        "enrichment": ansimarkup.parse("<light-yellow>"),
        "warning": ansimarkup.parse("<light-yellow>"),
        "query": ansimarkup.parse("<white>"),
    }
)


def colored_output(function):
    """Decorator that converts ansi markup into ansi escape sequences.

    :param function: Function that will return text using ansi markup.
    :type function: callable
    :returns: Wrapped function that converts markup into escape sequences.
    :rtype: callable

    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        output = function(*args, **kwargs)
        return ANSI_MARKUP(output)

    return wrapper


def json_formatter(result, verbose=False):
    """Format result as json."""
    return json.dumps(result, indent=4)


@colored_output
def analyze_formatter(results, verbose):
    """Convert Analyze output into human-readable text."""
    template = JINJA2_ENV.get_template("analyze_result_multi.txt.j2")

    # calculate total stats
    result = next(iter(results.values()))
    summary_stats = {
        'total_messages': len(results),
        'total_rules': len(result['rule_results']),
        'total_queries': len(result['query_results']),
    }
    
    # separate matched messages from unmatched ones and clear out unflagged rules
    flagged_messages = []
    unflagged_messages = []
    all_flagged_rules = set()
    for _, result in results.items():
        flagged_rules = []
        for rule in result['rule_results']:
            if rule['result']:
                flagged_rules.append(rule)
                all_flagged_rules.add(rule['name']+rule['source']) # no unique identifier

        result['rule_results'] = flagged_rules
        if len(flagged_rules) > 0:
            flagged_messages.append(result)
        else:
            unflagged_messages.append(result)

    # calculate flagged stats
    summary_stats['flagged_rules'] = len(all_flagged_rules)
    summary_stats['flagged_messages'] = len(flagged_messages)

    # sort each list of messages 
    # flagged_messages = sorted(
    #       flagged_messages,
    #       key=lambda i: i['name'].lower() if i.get('name') else '')

    rule_results, query_results = result["rule_results"], result["query_results"]


    return template.render(
            stats=summary_stats,
            flagged_messages=flagged_messages,
            unflagged_messages=unflagged_messages,
            rules=rule_results,
            queries=query_results,
            verbose=verbose)


def mdm_formatter(results, verbose):
    """Convert Message Data Model into human-readable text."""
    gron_output = gron.gron(json.dumps(results))
    gron_output = gron_output.replace('json = {}', 'message_data_model = {}')
    gron_output = re.sub(r'\njson\.', '\n', gron_output)

    return gron_output

    # template = JINJA2_ENV.get_template("message_data_model.txt.j2")
    # return template.render(results=results, verbose=verbose)


def format_mql(mql):
    mql = mql.replace("&&", "\n  &&")
    mql = mql.replace("||", "\n  ||")
    mql = mql.replace("],", "],\n  ")

    return mql

@colored_output
def me_formatter(result, verbose):
    """Convert 'me' output into human-readable text."""
    template = JINJA2_ENV.get_template("me_result.txt.j2")

    return template.render(result=result, verbose=verbose)

@colored_output
def feedback_formatter(result, verbose):
    """Convert 'feedback' output into human-readable text."""
    template = JINJA2_ENV.get_template("feedback_result.txt.j2")

    return template.render(result=result, verbose=verbose)


FORMATTERS = {
    "json": json_formatter,
    "txt": {
        "me": me_formatter,
        "feedback": feedback_formatter,
        "create": mdm_formatter,
        "analyze": analyze_formatter
    },
}
