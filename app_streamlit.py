import os
import io
import zipfile
import tempfile
import streamlit as st
from engine_master import EngineOSMasterPipeline

st.set_page_config(page_title="Engine OS Converter Bridge", page_icon="🎧", layout="centered")

st.title("Rekordbox ➔ Engine OS Converter")
st.write("Convert your Rekordbox XML library into a native Engine OS database format.")

uploaded_xml = st.file_uploader("Upload Rekordbox XML Export", type=["xml"])

if uploaded_xml is not None:
    if st.button("Start Conversion", type="primary"):
        with st.spinner("Processing tracks, cues, loops, and playlists..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                xml_path = os.path.join(temp_dir, "uploaded_rekordbox.xml")
                with open(xml_path, "wb") as f:
                    f.write(uploaded_xml.getbuffer())

                output_drive_dir = os.path.join(temp_dir, "Engine_USB_Export")
                
                pipeline = EngineOSMasterPipeline(drive_root_path=output_drive_dir)
                pipeline.initialize_drive_environment()
                pipeline.import_rekordbox_xml(xml_path)
                pipeline.close()

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for root, dirs, files in os.walk(output_drive_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, start=output_drive_dir)
                            zip_file.write(full_path, arcname)

                zip_buffer.seek(0)

                st.success("Conversion completed successfully!")
                st.download_button(
                    label="Download Engine OS Storage Package (.zip)",
                    data=zip_buffer,
                    file_name="Engine_OS_USB_Package.zip",
                    mime="application/zip"
                )
