#!/usr/bin/env python

""" Usage: crondiff.py [--test <rulename>] """

import os
import os.path
import yaml
import sys
import difflib

import requests
import pyquery
import docopt

basedir = os.path.dirname(os.path.realpath(__file__))
cachebasedir = os.path.join(basedir, "cache")
rulesbasedir = os.path.join(basedir, "rules.d")
rules = filter(lambda f: not f.startswith("."), os.listdir(rulesbasedir))

class RefreshFailedException(Exception):
    pass

def refresh_rule(rulename):

    rulefile = os.path.join(rulesbasedir, rulename)
    rule = yaml.load(file(rulefile))

    def transform(element):
        if rule["compare"] == u"text":
            return element.text_content()
        else:
            raise NotImplemented()

    r = requests.get(rule["url"])

    if r.status_code != requests.codes.ok:
        print "rule '%s' failed with status code: %d" % (rulename, r.status_code)
        raise RefreshFailedException()

    q = pyquery.PyQuery(r.text)
    return map(transform, q(rule["selector"]))

def check_all_rules():
    for rulename in rules:

        # fetch a fresh document from the website
        try:
            document = refresh_rule(rulename)
        except RefreshFailedException:
            continue

        # fetch the old document from cache or return empty document if not found
        try:
            with file(os.path.join(cachebasedir, rulename), "r") as cache:
                previous = cache.read().decode("utf-8").splitlines()
        except IOError:
            previous = []

        header_printed = False

        # perform a diff, but strip out metadata
        for line in difflib.context_diff(previous, document, n=0):

            if line.startswith("***") or line.startswith("---"):
                continue
            
            if not header_printed:
                print "*** diffs in rule '%s' ***" % rulename
                header_printed = True
            
            sys.stdout.write(line)
        
        # write the new document to the cache if not inhibited
        with file(os.path.join(cachebasedir, rulename), "w") as cache:
            cache.write("\n".join(document).encode("utf-8"))


if __name__ == '__main__':
    
    args = docopt.docopt(__doc__, version='crondiff 0.1')
    
    if args["--test"]:
        document = refresh_rule(args["<rulename>"])
        for line in document:
            print line
    else:
        check_all_rules()
