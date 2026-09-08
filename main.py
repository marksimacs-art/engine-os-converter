import os
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from engine_master import EngineOSMasterPipeline

app = FastAPI(title="Rekordbox to Engine OS API")

# Enable CORS so Lovable's web app can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Engine OS Conversion API is active"}

@app.post("/convert")
async def convert_rekordbox_xml(file: UploadFile = File(...)):
    temp_dir = "./temp_processing"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save incoming uploaded XML file temporarily
    xml_path = os.path.join(temp_dir, "uploaded_rekordbox.xml")
    with open(xml_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    output_drive_dir = os.path.join(temp_dir, "Engine_USB_Export")
    
    # Run core Python engine pipeline
    pipeline = EngineOSMasterPipeline(drive_root_path=output_drive_dir)
    pipeline.initialize_drive_environment()
    pipeline.import_rekordbox_xml(xml_path)
    pipeline.close()
    
    # Zip output directory into downloadable file
    zip_path = os.path.join(temp_dir, "Engine_OS_USB_Package")
    archive_format = "zip"
    shutil.make_archive(zip_path, archive_format, output_drive_dir)
    
    final_zip = f"{zip_path}.zip"
    return FileResponse(
        path=final_zip, 
        filename="Engine_OS_USB_Package.zip", 
        media_type="application/zip"
    )
