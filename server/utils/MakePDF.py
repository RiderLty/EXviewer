from typing import List
from PyPDF2 import PdfWriter, PdfReader
from PIL import Image
from io import BytesIO


def img2pdf(imgList: List[str]) -> BytesIO:
    imgObjList = [Image.open(x) for x in imgList]
    maxWidth = max(imgObj.width for imgObj in imgObjList)
    pdf = PdfWriter()
    for imgObj in imgObjList:
        # NEAREST,LANCZOS,BILINEAR,BICUBIC,BOX,HAMMING,
        imgObj = imgObj.resize((maxWidth, imgObj.height * maxWidth //
                                imgObj.width), resample=Image.LANCZOS)
        imgObj = imgObj.convert("RGB")
        imgIO = BytesIO()
        imgObj.save(imgIO, format="PDF")
        pdf.add_page(PdfReader(imgIO).pages[0])
    out = BytesIO()
    pdf.write(out)
    return out


pdfio = img2pdf([
    rf"C:\Users\lty\Pictures\Manga\0001_第1卷\{x:08d}.jpg"
    for x in range(1,193)

])

with open(r"C:\Users\lty\Pictures\test.pdf", 'wb') as f:
    f.write(pdfio.getvalue())
