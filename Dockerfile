FROM python:3.9-alpine
#FROM python:3.9-slim-buster
ADD ./ /EXviewer
RUN rm -rf /EXviewer/.github /EXviewer/.vscode /EXviewer/Screenshot /EXviewer/public /EXviewer/server/dist /EXviewer/server/termux-extend-libs /EXviewer/server/tools
WORKDIR /EXviewer
RUN apt-get install python3-lxml
RUN pip install -r ./requirements.txt
ENV EH_CACHE_PATH /cache
ENV EH_DOWNLOAD_PATH /Download
CMD ["python", "server"]
