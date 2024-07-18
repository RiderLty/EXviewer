# # 这个最小 但是只有amd64成功了
# FROM python:3.9-slim-buster 

# # 这个兼容最好 可以安装成功所有的
# # FROM python:3.9.6-buster

# ADD ./ /EXviewer
# RUN rm -rf /EXviewer/.github /EXviewer/.vscode /EXviewer/Screenshot /EXviewer/public /EXviewer/server/dist /EXviewer/server/termux-extend-libs /EXviewer/server/tools
# WORKDIR /EXviewer
# # RUN apt-get install python3-lxml
# RUN apt-get update
# RUN apt-get -y install python3-lxml 
# RUN pip install -r ./requirements.txt
# ENV EH_CACHE_PATH /cache
# ENV EH_DOWNLOAD_PATH /Download
# CMD ["python", "server"]

# FROM python:3.9 AS builder
# ADD ./ /EXviewer
# WORKDIR /EXviewer
# RUN apt-get update
# RUN apt-get -y install python3-lxml  build-essential patchelf
# RUN pip install -r ./requirements.txt && pip install pyinstaller
# RUN cd server && pyinstaller __main__.py -F -p ./ --name exviewer -i ../build/favicon.ico --add-data "../build:build"
# # RUN staticx /EXviewer/server/dist/exviewer /exviewer
# # RUN /EXviewer/server/dist/exviewer

# # FROM python:3.9-slim-buster 
# FROM python:3.9-slim
# COPY --from=builder /EXviewer/server/dist/exviewer  /exviewer
# ENV EH_CACHE_PATH=/cache
# ENV EH_DOWNLOAD_PATH=/Download
# CMD [/exviewer]





FROM riderlty/python-with-packages:latest AS builder
ADD ./ /EXviewer
WORKDIR /EXviewer
RUN cd server && pyinstaller __main__.py -F -p ./ --name exviewer -i ../build/favicon.ico --add-data "../build:build"
# RUN staticx /EXviewer/server/dist/exviewer /exviewer
# RUN /EXviewer/server/dist/exviewer

# FROM python:3.9-slim-buster 
FROM python:3.9-slim
COPY --from=builder /EXviewer/server/dist/exviewer  /exviewer
ENV EH_CACHE_PATH=/cache
ENV EH_DOWNLOAD_PATH=/Download
CMD [/exviewer]



