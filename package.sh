#!/bin/bash

# Define output file
OUTPUT="deploy_moscowle.zip"

# Remove old zip if exists
if [ -f "$OUTPUT" ]; then
    rm "$OUTPUT"
fi

# Ensure instance/uploads exists and has a placeholder
mkdir -p instance/uploads
touch instance/uploads/.gitkeep

# Update requirements.txt uses update_reqs.py logic or assume it is done.
# It is already done in previous steps.

# Create Zip
# We include specific files/folders to keep it clean.
echo "Creating archive $OUTPUT..."

zip -r "$OUTPUT" \
    app \
    ai_models \
    migrations \
    scripts \
    instance \
    config.py \
    passenger_wsgi.py \
    requirements.txt \
    run.py \
    INSTRUCCIONES_DESPLIEGUE_DIRECTADMIN.md \
    INSTRUCCIONES_DESPLIEGUE_CPANEL.md \
    -x "**/.DS_Store" \
    -x "**/*.pyc" \
    -x "**/__pycache__/*" \
    -x "instance/*.db" \
    -x "instance/test_*" \
    -x "instance/uploads/*"

# Clean up placeholder if we don't want it locally? No, it's fine.

echo "Done! Upload $OUTPUT to your DirectAdmin server."
