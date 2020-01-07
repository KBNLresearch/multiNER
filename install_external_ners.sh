
if [ ! -f dbpedia-spotlight-1.0.0.jar ]; then
    wget https://downloads.sourceforge.net/project/dbpedia-spotlight/spotlight/dbpedia-spotlight-1.0.0.jar
fi

if [ ! -f nl.tar.gz ]; then
    wget https://downloads.sourceforge.net/project/dbpedia-spotlight/2016-10/nl/model/nl.tar.gz
    tar xzf nl.tar.gz
fi

if [ ! -f stanford-ner-2018-10-16.zip ]; then
    wget https://nlp.stanford.edu/software/stanford-ner-2018-10-16.zip
    unzip stanford-ner-2018-10-16.zip
fi

if [ ! -f dutch.crf.gz ]; then
    wget https://github.com/WillemJan/Narralyzer_Dutch_languagemodel/raw/master/dutch.crf.gz
fi

polyglot download embeddings2.nl ner2.nl
python3 -m spacy download nl
python3 -m spacy download de
python3 - <<'EOF'
from flair.models import SequenceTagger
from flair.data import Sentence
nlp_flair = SequenceTagger.load('ner-multi')
EOF
