import os
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# AWS S3 configuration
s3_client = boto3.client('s3')

# Define the bucket name
bucket_name = 'channel-automation-workstore'

@app.route('/')
def index():
    # This will list the top-level folders in the S3 bucket
    response = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    folders = response.get('CommonPrefixes', [])
    return render_template('index.html', folders=folders)

@app.route('/browse')
def browse():
    # This will list the top-level folders
    response = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    folders = response.get('CommonPrefixes', [])
    return render_template('browse.html', folders=folders)


# @app.route('/browse/<path:folder_name>', methods=['GET', 'POST'])
# def browse_folder(folder_name):
#     try:
#         # This handles file deletion
#         if request.method == 'POST':
#             # Get the selected files from the form
#             selected_files = request.form.getlist('files')

#             # Delete the selected files from S3
#             for file_key in selected_files:
#                 s3_client.delete_object(Bucket=bucket_name, Key=file_key)

#             # Collect the deleted files to display the history
#             deleted_files = selected_files

#             # Reload the folder contents after deletion
#             response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_name + '/', Delimiter='/')
#             folders = response.get('CommonPrefixes', [])
#             files = response.get('Contents', [])
#             file_names = [file['Key'] for file in files if file['Key'] != folder_name + '/']

#             return render_template('browse_folder.html', folder_name=folder_name, folders=folders, files=file_names, deleted_files=deleted_files)

#         # GET request (initial load)
#         response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_name + '/', Delimiter='/')
#         folders = response.get('CommonPrefixes', [])
#         files = response.get('Contents', [])
#         file_names = [file['Key'] for file in files if file['Key'] != folder_name + '/']

#         return render_template('browse_folder.html', folder_name=folder_name, folders=folders, files=file_names)

#     except Exception as e:
#         print(f"Error: {e}")
#         return render_template('error.html', error_message="Error fetching folder contents.")

# @app.route('/browse/<path:folder_name>', methods=['GET', 'POST'])
# def browse_folder(folder_name):
#     if not folder_name.endswith('/'):
#         folder_name += '/'
#     if request.method == 'POST':
#         selected_files = request.form.getlist('files')
#         for file_key in selected_files:
#             s3_client.delete_object(Bucket=bucket_name, Key=file_key)
#         return redirect(url_for('browse_folder', folder_name=folder_name))
#     paginator = s3_client.get_paginator('list_objects_v2')
#     pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_name)
#     subfolders = set()
#     files = []
#     for page in pages:
#         for obj in page.get('Contents', []):
#             key = obj['Key']
#             if key.endswith('/'):
#                 continue
#             subpath = key[len(folder_name):]
#             if '/' in subpath:
#                 subfolder = subpath.split('/')[0]
#                 subfolders.add(folder_name + subfolder + '/')
#             else:
#                 files.append(key)
#     return render_template('browse_folder.html',
#                            folder_name=folder_name.rstrip('/'),
#                            folders=sorted(subfolders),
#                            files=sorted(files))



@app.route('/browse/<path:folder_name>', methods=['GET', 'POST'])
def browse_folder(folder_name):
    prefix = folder_name if folder_name.endswith('/') else folder_name + '/'

    if request.method == 'POST':
        selected_files = request.form.getlist('files')
        deleted_files = []
        for file_key in selected_files:
            s3_client.delete_object(Bucket=bucket_name, Key=file_key)
            deleted_files.append(file_key)
        flash(f"Deleted {len(deleted_files)} file(s).")
        return redirect(url_for('browse_folder', folder_name=folder_name))

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    folders = set()
    files = []

    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('/'):
                continue
            stripped_key = key[len(prefix):]
            if '/' in stripped_key:
                subfolder = stripped_key.split('/')[0]
                folders.add(f"{prefix}{subfolder}/")
            else:
                files.append(key)

    # Prepare folder links as tuples (full_path, display_name)
    folder_links = []
    for subfolder in sorted(folders):
        display_name = subfolder[len(prefix):-1]
        folder_links.append((subfolder, display_name))

    return render_template('browse_folder.html',
                           folder_name=folder_name,
                           folders=folder_links,
                           files=files)





@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

    if request.method == 'POST':
        # Handle file upload logic here
        category = request.form['category']
        files = request.files.getlist('file[]')
        uploaded_files = []

        for file in files:
            file_path = secure_filename(file.filename)
            folder_path = f"Unprocessed/{category}/"
            s3_client.upload_fileobj(file, bucket_name, folder_path + file_path)
            uploaded_files.append(file.filename)

        return render_template('upload.html', uploaded_files=uploaded_files, folder=folder_path)


@app.route('/delete', methods=['POST'])
def delete_files():
    files_to_delete = request.form.getlist('files')
    for file_key in files_to_delete:
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)