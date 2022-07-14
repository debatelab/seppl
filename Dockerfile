FROM nvidia/cuda:11.2.0-cudnn8-runtime-ubuntu20.04

LABEL maintainer "Gregor Betz  <gregor.betz@gmail.com>"

# Copy local code to the container image.
ENV APP_HOME .

WORKDIR $APP_HOME
COPY . ./

# --------------- Install python  ---------------

RUN apt update
RUN apt install -y python3 python3-pip
RUN python3 -m pip install --no-cache-dir --upgrade pip

# --------------- Install python packages using `pip` ---------------

RUN python3 -m pip install --no-cache-dir -r requirements.txt \
	&& rm -rf requirements.txt

# --------------- Configure Streamlit ---------------
RUN mkdir -p /root/.streamlit

COPY ./.streamlit/secrets.toml /root/.streamlit/secrets.toml
#RUN bash c 'cp ./.streamlit/secrets.toml /root/.streamlit/secrets.toml'

RUN bash -c 'echo -e "\
	[server]\n\
	enableCORS = false\n\
    enableXsrfProtection = false\n\
	" > /root/.streamlit/config.toml'

EXPOSE 8501
EXPOSE 8080

# --------------- Export envirennement variable ---------------
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

CMD ["streamlit", "run", "--server.port", "8501", "da2-inspector/app.py"]
#CMD ["streamlit", "run", "--server.port", "8080", "main.py"]