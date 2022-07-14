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

RUN python3 -m pip install --user pipx
RUN python3 -m pipx ensurepath
# --------------- Install python packages using `pip` ---------------

# System deps:
RUN python3 -m pipx install poetry==1.1.12
#RUN poetry config virtualenvs.create false \
#  && poetry install --no-dev --no-interaction --no-ansi
RUN poetry install --no-interaction --no-ansi

#RUN python3 -m pip install --no-cache-dir -r requirements.txt \
#	&& rm -rf requirements.txt

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

# --------------- Export environment variable ---------------
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

CMD ["poetry", "run", "streamlit", "run", "--server.port", "8501", "seppl/streamlit_app2.py"]
#CMD ["streamlit", "run", "--server.port", "8080", "main.py"]