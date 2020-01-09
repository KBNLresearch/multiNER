FROM debian:stable

RUN echo "deb http://ftp.debian.nl/debian/ sid main non-free contrib" >> /etc/apt/sources.list

COPY requirements.txt /tmp

RUN apt-get update && \
    apt-get install -y python3-numpy libicu-dev python3 python3-pip pkg-config default-jre unzip openjdk-8-jre-headless wget
    
RUN pip3 install Pillow==6.1

RUN pip3 install -r /tmp/requirements.txt

COPY ner.py /bin/ner.py

COPY install_external_ners.sh /bin/
RUN chmod +x /bin/install_external_ners.sh
RUN /bin/install_external_ners.sh

ADD run.sh /bin/run.sh
ADD run_external_ners.sh /bin/run_external_ners.sh

RUN chmod +x /bin/run.sh
RUN chmod +x /bin/run_external_ners.sh

CMD ["/bin/run.sh"]

EXPOSE 8099
