MultiNER combines the output from four different named-entity recognition (https://en.wikipedia.org/wiki/Named-entity_recognition) packages into one answer.

This software is part of the dac (https://github.com/KBNLresearch/dac) project,
Entity linker for the Dutch historical newspaper collection of the National Library of the Netherlands.

We've noticed a lot of misclassifications in our NER setup, so we've decided to combine the ouput of different NER packages.
The following packages are used:

    - Stanford NER (https://nlp.stanford.edu/software/CRF-NER.shtml)
    - spaCy (https://spacy.io/)
    - polyglot (http://polyglot.readthedocs.io/)
    - DBpedia Spotlight (https://www.dbpedia-spotlight.org/)
    - Flair (https://github.com/zalandoresearch/flair)

In our setup Stanford and Spotlight are the leading NER package's (So all these show up in the integrated results), only if 2 other NER packages agree on a NE, the answer show's up in the integrated results. If just Spotlight or Stanford see an NE, and none agree, it will still show up in the end result.

Example response:

    "count": 3,
    "type_certainty": 2,
    "type": "person",
    "right_context": "zich mij te vragen, of",
    "pos": 1324,
    "ne_context": "Manchon",
    "ne": "Manchon",
    "ner_src": [
        "stanford",
        "spacy",
        "polyglot"
    ],
    "left_context": "op zijn allerlaatst verwaardigde mevrouw",
    "types": [
        "person",
        "location"
    ]

In the example 3 NER packages have figured out "Manchon" is a NE,
two of them agree that it is a person, and one thinks it's a location.
Hence count: 3 and type_certainty 2. ner_src show's which packages think the current NE is a NE (in this case all of them).
The context shows the surroundings of the NE.

All this information is picked-up by dac to weigh a possible match in WikiData/DBPedia.

MultiNER has only been tested using python 3, and is open-source with a MIT Licence.

==

Install notes:

See ner.py / Dockerfile and *.sh files for details.

Or run from docker:

docker build -t multiner:latest .

docker run -i -p 8099:8099 multiner:latest run.sh
