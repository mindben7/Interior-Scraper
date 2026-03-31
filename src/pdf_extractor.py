import fitz
import io
import aiohttp
import os
from PIL import Image

async def extract_pdf_images(pdf_url):
    print(f"[*] Native PDF Archival Rip: {pdf_url}")
    # Download buffer
    async with aiohttp.ClientSession() as session:
        async with session.get(pdf_url) as resp:
            if resp.status != 200:
                print(f"[-] Failed to download PDF. Status: {resp.status}")
                return []
            pdf_bytes = await resp.read()
            
    doc = fitz.open("pdf", pdf_bytes)
    images_to_eval = []
    print(f"[*] PDF Stream Loaded. Ripping raw high-res master frames across {len(doc)} pages...")
    
    extracted_count = 0
    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                width = img[2]
                height = img[3]
                
                # Minimum resolution for a valid photograph/scan (ignoring tiny icons/logos)
                if width > 600 and height > 600:
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        ext = base_image["ext"]
                        
                        image = Image.open(io.BytesIO(image_bytes))
                        if image.mode == 'CMYK':
                            image = image.convert('RGB')
                            
                        filename = f"/tmp/pdf_extract_{page_num}_{img_index}_{xref}.{ext}"
                        image.save(filename)
                        
                        images_to_eval.append({
                            'url': f"file://{filename}",
                            'width': width,
                            'height': height,
                            'alt': f"USModernist Page {page_num}",
                            'page_url': pdf_url
                        })
                        extracted_count += 1
                    except Exception as img_err:
                        pass
        except Exception as e:
            pass
            
    print(f"[+] Surgical ripper extracted {extracted_count} raw asset streams.")
    return images_to_eval
