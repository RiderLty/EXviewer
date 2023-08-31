from typing import List
from PyPDF2 import PdfWriter, PdfReader
from PIL import Image
from io import BytesIO
from time import time



def img2pdf(imgList: List[str]) -> BytesIO:
    imgObjList = [Image.open(x) for x in imgList]
    # scaleWidth = max(imgObj.width for imgObj in imgObjList)
    scaleWidth = imgObjList[0].width
    pdf = PdfWriter()
    for imgObj in imgObjList:
        # NEAREST,LANCZOS,BILINEAR,BICUBIC,BOX,HAMMING,
        if scaleWidth != imgObj.width:
            imgObj = imgObj.resize((scaleWidth, imgObj.height * scaleWidth //imgObj.width), resample=Image.LANCZOS)
        imgIO = BytesIO()
        imgObj.save(imgIO, format="PDF")
        pdf.add_page(PdfReader(imgIO).pages[0])
    out = BytesIO()
    pdf.write(out)
    return out


if __name__ == "__main__":
    print("test start")
    pdfio = img2pdf([
    rf"D:\EHDownloads\Gallery\2659671_21e8dcbebd\{x:08d}.jpg"
        for x in range(1,205)
    ])

    with open(r"P:\test.pdf", 'wb') as f:
        f.write(pdfio.getvalue())
