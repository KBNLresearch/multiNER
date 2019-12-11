FROM debian:stable

COPY requirements.txt /tmp

RUN apt-get update && \
    apt-get install -y python3-numpy libicu-dev python3 python3-pip pkg-config

RUN pip3 install -r /tmp/requirements.txt

COPY ner.py /bin/ner.py

RUN polyglot download embeddings2.nl ner2.nl
RUN python3 -m spacy download nl
RUN python3 -m spacy download de

ADD run.sh /bin/run.sh
RUN chmod +x /bin/run.sh

EXPOSE 8099
