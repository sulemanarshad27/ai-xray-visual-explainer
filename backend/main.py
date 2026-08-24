import io
import json
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import google.generativeai as genai

app = FastAPI()

# THE FIX: FORCE FULL ACCESS HEADERS SO YOUR BROWSER UNBLOCKS VERCEL
# FORCE RECOGNIZED ORIGINS PATHWAYS TO BUST THROUGH BROWSER CORING CHECKS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://vercel.app",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...), 
    x_api_key: str = Header(None, alias="X-API-Key")
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Token missing from header.")
    
    try:
        genai.configure(api_key=x_api_key)
        
        # Read the incoming image file bytes
        image_bytes = await file.read()
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        
        # Free Tier File Optimization: Downscale size
        max_size = 800
        width, height = img.size
        if width > max_size or height > max_size:
            img.thumbnail((max_size, max_size))
            
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        optimized_bytes = buffer.getvalue()
        
        # Target the active high-power engine model string configuration
        model = genai.GenerativeModel('gemini-3.6-flash')
        
        instruction = (
            "Deconstruct this entire image canvas comprehensively. Identify the maximum possible "
            "number of components, distinct objects, specific accessories, structural parts, "
            "textures, patterns, and individual items present across the layout. Do not limit the count. "
            "For every single detected element, provide its exact bounding location using normalized coordinate formatting values "
            "scaled from 0 to 1000 written exactly like: [ymin, xmin, ymax, xmax]. "
            "Return the complete dataset payload ONLY as a valid raw unformatted JSON array block, "
            "no backticks, no markdown text wrappers. "
            "Follow this scheme structure directly: "
            "[{\"name\": \"Item Name\", \"box\": [ymin, xmin, ymax, xmax], \"explanation\": \"1-sentence engineering functional details.\"}]"
        )
        
        response = model.generate_content([
            instruction,
            {"mime_type": "image/jpeg", "data": optimized_bytes}
        ])
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data_payload = json.loads(clean_text)
        return data_payload
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
