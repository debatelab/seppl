FROM ubuntu:18.04

# python:3.9-slim

LABEL maintainer "Gregor Betz  <gregor.betz@gmail.com>"

# Copy local code to the container image.
ENV APP_HOME . 

WORKDIR $APP_HOME
COPY . ./

# --------------- Install python  ---------------

RUN apt update
RUN apt install -y python3 python3-pip
RUN python3 -m pip install --no-cache-dir --upgrade pip

# --------------- Install poetry and package using `pip` ---------------

# System deps:
RUN pip install poetry==1.2.1
RUN poetry self add poetry-dotenv-plugin
RUN poetry install --no-interaction --no-ansi --without dev


# --------------- Configure Prover ---------------

RUN apt install -y prover9

# --------------- Configure Streamlit ---------------
RUN mkdir -p /root/.streamlit

COPY ./.streamlit/secrets.toml /root/.streamlit/secrets.toml

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
