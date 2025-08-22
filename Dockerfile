# # 这个最小 但是只有amd64成功了
# FROM python:3.9-slim-buster 

# 这个兼容最好 可以安装成功所有的
# FROM python:3.9.6-buster


FROM python:3.9

ADD ./ /Exviewer
WORKDIR /Exviewer
# RUN apt-get install python3-lxml
RUN apt-get update && apt-get -y install python3-lxml && pip install -r ./requirements.txt 
ENV EH_CACHE_PATH /cache
ENV EH_DOWNLOAD_PATH /Download
CMD ["python", "/Exviewer/server"]



              # linux/arm/v7
              # linux/arm/v8
              # linux/arm64


              

# FROM python:3.9 AS builder
# ADD ./ /Exviewer
# WORKDIR /Exviewer
# RUN apt-get update
# RUN apt-get -y install python3-lxml  build-essential patchelf
# RUN pip install -r ./requirements.txt && pip install pyinstaller
# RUN cd server && pyinstaller __main__.py -F -p ./ --name exviewer -i ../build/favicon.ico --add-data "../build:build"
# # RUN staticx /Exviewer/server/dist/exviewer /exviewer
# # RUN /Exviewer/server/dist/exviewer

# # FROM python:3.9-slim-buster 
# FROM python:3.9-slim
# COPY --from=builder /Exviewer/server/dist/exviewer  /exviewer
# ENV EH_CACHE_PATH=/cache
# ENV EH_DOWNLOAD_PATH=/Download
# CMD [/exviewer]





# FROM riderlty/python-with-packages:latest AS builder
# ADD ./ /Exviewer
# WORKDIR /Exviewer
# RUN cd server && pyinstaller __main__.py -F -p ./ --name exviewer -i ../build/favicon.ico --add-data "../build:build"
# # RUN staticx /Exviewer/server/dist/exviewer /exviewer
# # RUN /Exviewer/server/dist/exviewer

# # FROM python:3.9-slim-buster 
# FROM python:3.9-slim
# COPY --from=builder /Exviewer/server/dist/exviewer  /exviewer
# ENV EH_CACHE_PATH=/cache
# ENV EH_DOWNLOAD_PATH=/Download
# CMD [/exviewer]



