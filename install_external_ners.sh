wget https://downloads.sourceforge.net/project/dbpedia-spotlight/spotlight/dbpedia-spotlight-1.0.0.jar
wget https://downloads.sourceforge.net/project/dbpedia-spotlight/2016-10/nl/model/nl.tar.gz
tar xzf nl.tar.gz
wget https://nlp.stanford.edu/software/stanford-ner-2018-10-16.zip
wget https://github.com/WillemJan/Narralyzer_Dutch_languagemodel/raw/master/dutch.crf.gz
unzip stanford-ner-2018-10-16.zip
polyglot download embeddings2.nl ner2.nl
python3 -m spacy download nl
python3 -m spacy download de
