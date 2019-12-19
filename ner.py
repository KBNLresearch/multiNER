#!/usr/bin/env python3
'''
MultiNER

MultiNER combines the output from five different
named-entity recognition packages into one answer.

https://github.com/KBNLresearch/MultiNER

Copyright 2013, 2019 Willem Jan Faber,
KB/National Library of the Netherlands.

To install most external dependencies using the following command:

    pip3 install -r requirements.txt
    ./install_external_ners.sh

For Stanford and Spotlight, see their own manuals on howto install those:

    https://nlp.stanford.edu/software/crf-faq.shtml#cc

    https://github.com/dbpedia-spotlight/dbpedia-spotlight/wiki/Run-from-a-JAR
    https://github.com/dbpedia-spotlight/dbpedia-spotlight/

    Spotlight needs older java version 8 to run.

Once installed (With wanted language models), run the webservices so MultiNER can contact those:

    $ cd /path/to/stanford-ner-2018-10-16
    $ java -mx400m -cp stanford-ner.jar edu.stanford.nlp.ie.NERServer \
           -outputFormat inlineXML -encoding "utf-8" \
           -loadClassifier dutch.crf.gz -port 1234

    $ cd /path/to/spotlight
    $ java --add-modules java.xml.bind -jar dbpedia-spotlight-1.0.0.jar \
                         nl http://localhost:9090/rest

    There is a small shell-script (run_external_ners.sh) available for this,
    modify it to your needs, if you change port's or want to use an external server,
    please keep them in sync with this file (STANFORD_HOST/PORT, SPOTLIGHT_HOST/PORT).

Language models spacy, polyglot and flair:

    There is a big try catch block surrounding the invocation of polyglot,
    there is a good reason for that, I cannot seem to be able to force it to
    use a specific language, it will do a lang-detect and handle on that info.
    If the guessed language is not present, it will throw an exception.

    You can soft-link mutiple languages to other languages, to fool the software
    into using a wanted language, for example:

    $ cd ~/polyglot_data/ner2; mkdir af; ln -s ./nl/nl_ner.pkl.tar.bz2 ./af/af_ner.pkl.tar.bz2

    # apt-get install python-numpy libicu-dev
    $ pip install polyglot
    $ polyglot download embeddings2.nl

    $ python -m spacy download nl
    $ python -m spacy download de
    $ python -m spacy download fr
    $ python -m spacy download nl
    $ python -m spacy download en

    Flair will automaticaly download the language model on firstrun.


Running test, and stable web-service:

    $ python3 ./ner.py

    This will run the doctest, if everything works, and external services are up,
    0 errors should be the result.

    $ gunicorn -w 10 web:application -b :8099

    Afther this the service can be envoked like this:

    $ curl -s localhost:8099/?url=http://resolver.kb.nl/resolve?urn=ddd:010381561:mpeg21:a0049:ocr

    If you expect to process a lot:

    # echo 1 > /proc/sys/ipv4/tcp_tw_recycle

    Else there will be no socket's left to process.

'''
import ast
import json
import lxml.html
import requests
import spacy
import telnetlib
import threading
import operator

from flask import request, Response, Flask
from lxml import etree
from polyglot.text import Text

from flair.models import SequenceTagger
from flair.data import Sentence

application = Flask(__name__)
application.debug = True

# Preload Dutch data.
nlp_spacy = spacy.load('nl')
nlp_flair = SequenceTagger.load('ner-multi')

# Will be used in web-service and doctest.
EXAMPLE_URL = "http://resolver.kb.nl/resolve?"
EXAMPLE_URL += "urn=ddd:010381561:mpeg21:a0049:ocr"

# Baseurl for Stanford standalone NER setup.
# https://nlp.stanford.edu/software/crf-faq.shtml#cc
# (Use inlineXML)
STANFORD_HOST = "localhost"
STANFORD_PORT = 9092

# Baseurl for Spotlight rest-service.
# https://github.com/dbpedia-spotlight/dbpedia-spotlight/
SPOTLIGHT_HOST = "localhost"
SPOTLIGHT_PORT = "9091"
SPOTLIGHT_PATH = "/rest/annotate/"

# Timeout for external NER's (stanford, spotlight)
TIMEOUT = 1000


def context(text_org, ne, pos, context=5):
    '''
        Return the context of an NE, based on abs-pos,
        if there are 'context-tokens' in the way,
        skip those.

        Current defined context-tokens:
        ”„!,'\",`<>?-+"
    '''
    CONTEXT_TOKENS = "”„!,'\",`<>?-+\\"

    leftof = text_org[:pos].strip()
    l_context = " ".join(leftof.split()[-context:])

    rightof = text_org[pos + len(ne):].strip()
    r_context = " ".join(rightof.split()[:context])

    ne_context = ne

    try:
        if l_context[-1] in CONTEXT_TOKENS:
            ne_context = l_context[-1] + ne_context
    except Exception:
        pass

    try:
        if r_context[0] in CONTEXT_TOKENS:
            ne_context = ne_context + r_context[0]
    except Exception:
        pass

    return l_context, r_context, ne_context


def translate(input_str):
    '''
        Translate the labels to human-readable.
    '''
    input_str = input_str.lower()

    if input_str == "org":
        return 'organisation'
    if input_str == "per":
        return 'person'
    if input_str == "misc":
        return 'other'
    if input_str == "gpe":
        return 'location'
    if input_str == "loc":
        return 'location'
    return input_str


class Stanford(threading.Thread):
    '''
        Wrapper for Stanford.

        https://nlp.stanford.edu/software/CRF-NER.shtml

        >>> test = "Deze iets langere test bevat de naam Albert Einstein."
        >>> p = Stanford(parsed_text=test)
        >>> p.start()
        >>> import time
        >>> time.sleep(0.1)
        >>> from pprint import pprint
        >>> pprint(p.join())
        {'stanford': [{'ne': 'Albert Einstein', 'pos': 37, 'type': 'person'}]}
    '''

    def __init__(self, group=None, target=None,
                 name=None, parsed_text={}):

        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.parsed_text = parsed_text

    def run(self):
        self.result = {"stanford": []}

        text = self.parsed_text.replace('\n', ' ')

        done = False
        retry = 0
        max_retry = 10

        while not done and retry < max_retry:
            try:
                conn = telnetlib.Telnet(host=STANFORD_HOST,
                                        port=STANFORD_PORT,
                                        timeout=TIMEOUT)
                done = True
            except Exception:
                retry += 1

        if not done:
            self.result = {"stanford": []}
            return

        text = text.encode('utf-8') + b'\n'
        conn.write(text)
        raw_data = conn.read_all().decode('utf-8')
        conn.close()

        data = etree.fromstring('<root>' + raw_data + '</root>')

        result = []

        p_tag = ''
        for item in data.iter():
            if not item.tag == 'root':
                tag = item.tag.split('-')[1]
                if item.tag.split('-')[0] == 'I' and p_tag == tag:
                    result[-1]["ne"] = result[-1]["ne"] + ' ' + item.text
                else:
                    result.append({"ne": item.text,
                                   "type": translate(item.tag.split('-')[1])})
                    p_tag = tag

        offset = 0
        for i, ne in enumerate(result):
            ne = ne["ne"]
            pos = self.parsed_text[offset:].find(ne)
            result[i]["pos"] = pos + offset
            offset += pos + len(ne)

        self.result = {"stanford": result}

    def join(self):
        threading.Thread.join(self)
        return self.result


class Flair(threading.Thread):
    '''
        Wrapper for Flair.

        https://github.com/zalandoresearch/flair

        >>> test = "Deze iets langere test bevat de naam Albert Einstein."
        >>> f = Flair(parsed_text=test)
        >>> f.start()
        >>> import time
        >>> time.sleep(0.1)
        >>> from pprint import pprint
        >>> pprint(f.join())
        {'flair': [{'ne': 'Albert Einstein.', 'pos': 37, 'type': 'person'}]}
    '''
    def __init__(self, group=None, target=None,
                 name=None, parsed_text={}):

        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.parsed_text = parsed_text

    def run(self):
        sentence = [Sentence(self.parsed_text, use_tokenizer=False)]
        tagged = nlp_flair.predict(sentence)

        tagged_items = [
                s.to_dict(tag_type='ner').get('entities') for s in tagged
                ]

        self.result = []

        for item in tagged_items:
            for i in item:
                if not i:
                    continue
                self.result.append({
                    "ne": i.get('text'),
                    "pos": i.get('start_pos'),
                    "type": translate(i.get('type'))
                })

    def join(self):
        threading.Thread.join(self)
        return {"flair": self.result}


class Polyglot(threading.Thread):
    '''
        Wrapper for Polyglot.

        http://polyglot.readthedocs.io/en/latest/index.html

        >>> test = "Deze iets langere test bevat de naam Albert Einstein."
        >>> p = Polyglot(parsed_text=test)
        >>> p.start()
        >>> import time
        >>> time.sleep(0.1)
        >>> from pprint import pprint
        >>> pprint(p.join())
        {'polyglot': [{'ne': 'Albert Einstein', 'pos': 37, 'type': 'person'}]}
    '''

    def __init__(self, group=None, target=None,
                 name=None, parsed_text={}):

        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.parsed_text = parsed_text

    def run(self):
        buffer_all = []

        try:
            text = Text(self.parsed_text, hint_language_code='nl')

            for sent in text.sentences:
                entity_buffer = []
                prev_entity_start = -1
                for entity in sent.entities:
                    if entity not in entity_buffer:
                        # For some reason polyglot double's it's output.
                        if not prev_entity_start == entity.start:
                            prev_entity_start = entity.start
                            entity_buffer.append(entity)
                        else:
                            entity_buffer.pop()
                            entity_buffer.append(entity)

                for item in entity_buffer:
                    buffer_all.append(item)

            result = []
            for entity in buffer_all:
                # For there is no sane way to do this.
                ne = " ".join(ast.literal_eval(entity.__str__()))
                tag = str(entity.tag.split('-')[1])
                result.append({"ne": ne,
                               "type": translate(tag)})

            offset = 0
            for i, ne in enumerate(result):
                ne = ne["ne"]
                pos = self.parsed_text[offset:].find(ne)
                result[i]["pos"] = pos + offset
                offset += pos + len(ne)
        except Exception:
            result = []

        self.result = {"polyglot": result}

    def join(self):
        threading.Thread.join(self)
        return self.result


class Spacy(threading.Thread):
    '''
        Wrapper for Spacy.

        https://spacy.io/

        >>> test = "Deze iets langere test bevat de naam Einstein."
        >>> p = Spacy(parsed_text=test)
        >>> p.start()
        >>> import time
        >>> time.sleep(0.1)
        >>> from pprint import pprint
        >>> pprint(p.join())
        {'spacy': [{'ne': 'Einstein', 'pos': 37, 'type': 'location'}]}
    '''

    def __init__(self, group=None, target=None,
                 name=None, parsed_text={}):

        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.parsed_text = parsed_text

    def run(self):
        result = []
        try:
            doc = nlp_spacy(self.parsed_text)

            for ent in doc.ents:
                result.append({"ne": ent.text, "type": translate(ent.label_)})

            offset = 0
            for i, ne in enumerate(result):
                ne = ne["ne"]
                pos = self.parsed_text[offset:].find(ne)
                result[i]["pos"] = pos + offset
                offset += pos + len(ne)
        except Exception:
            pass

        self.result = {"spacy": result}

    def join(self):
        threading.Thread.join(self)
        return self.result


class Spotlight(threading.Thread):
    '''
        Wrapper for DBpedia-Spotlight.

        https://www.dbpedia-spotlight.org/
        >>> t = "Richard Nixon bakt een taart voor zichzelf."
        >>> p = Spotlight(parsed_text=t)
        >>> p.start()
        >>> import time
        >>> time.sleep(1)
        >>> from pprint import pprint
        >>> pprint(p.join())
        {'spotlight': [{'ne': 'Richard Nixon', 'pos': 0, 'type': 'other'}]}
    '''

    def __init__(self, group=None, target=None,
                 name=None, parsed_text={}, confidence='0.9'):

        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.parsed_text = parsed_text
        self.confidence = confidence

    def run(self):
        data = {'text': self.parsed_text,
                'confidence': str(self.confidence)}

        url = 'http://'
        url += SPOTLIGHT_HOST
        url += ':' + SPOTLIGHT_PORT
        url += SPOTLIGHT_PATH

        header = {"Accept": "application/json"}

        done = False
        retry = 0
        max_retry = 10

        while not done and retry < max_retry:
            try:
                response = requests.get(url,
                                        params=data,
                                        headers=header,
                                        timeout=TIMEOUT)

                data = response.json()
                result = []

                if data and data.get('Resources'):
                    for item in data.get('Resources'):
                        ne = {}
                        ne["ne"] = item.get('@surfaceForm')
                        ne["pos"] = int(item.get('@offset'))
                        ne["type"] = "other"
                        result.append(ne)

                self.result = {"spotlight": result}
                done = True
            except Exception:
                self.result = {"spotlight": []}
                retry += 1

    def join(self):
        threading.Thread.join(self)
        return self.result


def intergrate_results(result, source, source_text, context_len):
    new_result = {}
    res = []

    for ne in result.get("stanford"):
        res = {}
        res["count"] = 1
        res["ne"] = ne.get("ne")
        res["ner_src"] = ["stanford"]
        res["type"] = {ne.get("type"): 1}
        res["pref_type"] = ne.get("type")
        new_result[ne.get("pos")] = res

    for ne in result.get("spotlight"):
        if not ne.get("pos") in res:
            res = {}
            res["count"] = 1
            res["ne"] = ne.get("ne")
            res["ner_src"] = ["spotlight"]
            res["type"] = {ne.get("type"): 1}
            res["pref_type"] = ne.get("type")
            new_result[ne.get("pos")] = res
        else:
            new_result[ne.get("pos")]["count"] += 1
            new_result[ne.get("pos")]["ner_src"].append("spotlight")

            if not ne.get("type") in new_result[ne.get("pos")]["type"]:
                new_result[ne.get("pos")]["type"][ne.get("type")] = 1
            else:
                new_result[ne.get("pos")]["type"][ne.get("type")] += 1

    parsers = ["spacy", "polyglot", "flair"]

    for parser in parsers:
        if result.get(parser) is None:
            continue
        for ne in result.get(parser):
            if ne.get("pos") in new_result:

                if parser in new_result[ne.get("pos")]["ner_src"]:
                    continue

                new_result[ne.get("pos")]["count"] += 1
                new_result[ne.get("pos")]["ner_src"].append(parser)

                if ne.get("type") in new_result[ne.get("pos")]["type"]:
                    new_result[ne.get("pos")]["type"][ne.get("type")] += 1
                else:
                    new_result[ne.get("pos")]["type"][ne.get("type")] = 1

                if not ne.get("ne") == new_result[ne.get("pos")].get("ne"):
                    new_result[ne.get("pos")]["alt_ne"] = ne.get("ne")

            else:
                new_result[ne.get("pos")] = {
                    "count": 1,
                    "ne": ne.get("ne"),
                    "ner_src": [parser],
                    "type": {ne.get("type"): 1}}

    final_result = []
    for ne in new_result:
        if new_result[ne].get("pref_type") or \
                len(new_result[ne].get("ner_src")) == 2:
            if "pref_type" in new_result[ne]:
                ne_type = max_class(new_result[ne]["type"],
                                    new_result[ne]["pref_type"])
                new_result[ne].pop("pref_type")
            else:
                ne_type = max_class(new_result[ne]["type"],
                                    list(new_result[ne]["type"])[0])

            new_result[ne]["types"] = list(new_result[ne]["type"])
            new_result[ne]["type"] = ne_type[0]
            new_result[ne]["type_certainty"] = ne_type[1]

            new_result[ne]["left_context"], \
                new_result[ne]["right_context"], \
                new_result[ne]["ne_context"] = context(source_text,
                                                       new_result[ne]["ne"],
                                                       ne,
                                                       context_len)
            new_result[ne]["pos"] = ne
            new_result[ne]["source"] = source

            final_result.append(new_result[ne])

    final_result = sorted(final_result, key=operator.itemgetter('pos'))

    return final_result


def manual_find(input_str, source_text, source, context_len):
    '''
        Find occurrence of an 'ne' and
        get the left and right context.
    '''

    result = {}

    pos = source_text.find(input_str)
    result["pos"] = pos
    result["ne"] = input_str
    result["source"] = source
    result["type"] = 'manual'

    if not pos == -1:
        result["left_context"],
        result["right_context"],
        result["ne_context"] = context(source_text,
                                       input_str,
                                       pos,
                                       context_len)
    else:
        result["left_context"] = result["right_context"] = ''
        result["ne_context"] = input_str

    return result


def max_class(input_type={"LOC": 2, "MISC": 3}, pref_type="LOC"):
    mc = max(input_type, key=input_type.get)

    if input_type.get(mc) == 1:
        mc = pref_type
        sure = 1
    if input_type.get(mc) == 2:
        sure = 2
    if input_type.get(mc) == 3:
        sure = 3
    if input_type.get(mc) == 4:
        sure = 4

    return(mc, sure)


@application.route('/')
def index():
    parsers = {"polyglot": Polyglot,
               "spacy": Spacy,
               "spotlight": Spotlight,
               "stanford": Stanford}

    url = request.args.get('url')
    manual = request.args.get('ne')
    context_len = request.args.get('context')

    if not context_len:
        context_len = 5
    else:
        context_len = int(context_len)

    if not url:
        result = {"error": "Missing argument ?url=%s" % EXAMPLE_URL}
        resp = Response(response=json.dumps(result),
                        mimetype='application/json; charset=utf-8')
        return (resp)

    try:
        parsed_text = ocr_to_dict(url)
    except Exception:
        result = {"error": "Failed to fetch %s" % url}
        resp = Response(response=json.dumps(result),
                        mimetype='application/json; charset=utf-8')
        return (resp)

    result_all = {}

    fresult = []
    for part in parsed_text:
        result = {}
        tasks = []

        if manual:
            fresult.append(manual_find(manual,
                                       parsed_text[part],
                                       part,
                                       context_len))

        for p in parsers:
            tasks.append(parsers[p](parsed_text=parsed_text[part]))
            tasks[-1].start()

        for p in tasks:
            ner_result = p.join()
            result[list(ner_result)[0]] = ner_result[list(ner_result)[0]]

        result_all[part] = intergrate_results(result,
                                              part,
                                              parsed_text[part],
                                              context_len)

    for part in result_all:
        if result_all[part]:
            for item in result_all[part]:
                fresult.append(item)

    result = json.dumps({"entities": fresult,
                         "text": parsed_text})

    resp = Response(response=result,
                    mimetype='application/json; charset=utf-8')

    return (resp)


def ocr_to_dict(url):
    '''
        Fetch some OCR from the KB / Depher newspaper collection,
        remove the XML-tags, and put it into a dictionary:

        >>> EXAMPLE_URL = "http://resolver.kb.nl/resolve?"
        >>> EXAMPLE_URL += "urn=ddd:010381561:mpeg21:a0049:ocr"
        >>> ocr_to_dict(EXAMPLE_URL).get("title")
        'EERSTE HOOFDSTUK'
    '''

    done = False
    retry = 0

    while not done:
        try:
            req = requests.get(url, timeout=TIMEOUT)
            if req.status_code == 200:
                done = True
            retry += 1
            if retry > 50:
                done = True
        except Exception:
            done = False

    text = req.content
    text = text.decode('utf-8')

    parser = lxml.etree.XMLParser(ns_clean=False,
                                  recover=True,
                                  encoding='utf-8')

    xml = lxml.etree.fromstring(text.encode(), parser=parser)

    parsed_text = {}

    for item in xml.iter():
        if not item.text:
            continue

        item.text = item.text.replace('&', '&amp;')
        item.text = item.text.replace('>', '&gt;')
        item.text = item.text.replace('<', '&lt;')

        if item.tag == 'title':
            if "title" not in parsed_text:
                parsed_text["title"] = []
            parsed_text["title"].append(item.text)
        else:
            if "p" not in parsed_text:
                parsed_text["p"] = []
            parsed_text["p"].append(item.text)

    for part in parsed_text:
        parsed_text[part] = "".join(parsed_text[part])

    return parsed_text


def test_all():
    '''
    Example usage:

    >>> parsers = {
    ...            "polyglot": Polyglot,
    ...            "stanford": Stanford,
    ...            "flair" : Flair,
    ...            "spacy": Spacy,
    ...            "spotlight": Spotlight,
    ...           }

    >>> url = [EXAMPLE_URL]
    >>> parsed_text = ocr_to_dict(url[0])

    >>> tasks = []
    >>> result = {}

    >>> for p in parsers:
    ...     tasks.append(parsers[p](parsed_text=parsed_text["p"]))
    ...     tasks[-1].start()

    >>> import time
    >>> time.sleep(1)

    >>> for p in tasks:
    ...     ner_result = p.join()
    ...     result[list(ner_result)[0]] = ner_result[list(ner_result)[0]]

    >>> from pprint import pprint
    >>> pprint(intergrate_results(result, "p", parsed_text["p"], 5)[-1])
    {'count': 4,
     'left_context': 'als wie haar nadert streelt:',
     'ne': 'René',
     'ne_context': 'René',
     'ner_src': ['stanford', 'spacy', 'polyglot', 'flair'],
     'pos': 5597,
     'right_context': 'genoot van zijn charme als',
     'source': 'p',
     'type': 'person',
     'type_certainty': 4,
     'types': ['person']}
    '''
    return


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
