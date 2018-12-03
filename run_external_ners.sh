#!/usr/bin/env bash

tmux new-session -d -s "stanford_ner" "cd /home/ubuntu/stanford-ner-2018-10-16; java -mx400m -cp stanford-ner.jar edu.stanford.nlp.ie.NERServer -outputFormat inlineXML -encoding "utf-8" -loadClassifier dutch.crf.gz -port 1234"
tmux new-session -d -s "spotlight" "cd /home/ubuntu/spotlight; java --add-modules java.xml.bind -jar dbpedia-spotlight-1.0.0.jar nl http://localhost:9090/rest"

