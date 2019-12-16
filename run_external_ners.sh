#!/usr/bin/env bash

(java -mx400m -cp stanford-ner-2018-10-16/stanford-ner.jar edu.stanford.nlp.ie.NERServer -outputFormat inlineXML -encoding "utf-8" -loadClassifier dutch.crf.gz -port 9092) &

(/usr/lib/jvm/java-8-openjdk-amd64/bin/java -jar dbpedia-spotlight-1.0.0.jar nl http://localhost:9091/rest) &

