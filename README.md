# Thingiscrape
Thingiverse REST API python wrapper

## About <a name = "about"></a>
A python based [Thingiverse.com](https://www.thingiverse.com) object scraper and downloader. The program can search of objects using keywords, licenses, users, categories and then sort the results, for example returning the most popular or newest uploads.

## Getting Started 

First you need to install the requirements - there are not that many 😊.
```
pip install -r requirements.txt
```

### Setting Up Your Thingiverse API Token

Before using thingiscrape, you need to get an API token from Thingiverse:

1. **Create a Thingiverse Account** (if you don't already have one)
   - Visit [https://www.thingiverse.com](https://www.thingiverse.com) and sign up

2. **Register a Desktop App**
   - Go to [https://www.thingiverse.com/apps/create](https://www.thingiverse.com/apps/create)
   - Fill out the app registration form
   - **Note:** The "Create App" button is all white and may be hard to see at the bottom of the page
   - After creating the app, you will receive an **App Token**

3. **Add Your API Token to the Script**
   - Open `thingiscrape.py` in your text editor
   - Find line 25 which currently contains: `api_token = os.environ.get('API_TOKEN')`
   - Replace the token string with your own App Token from step 2
   - Save the file

Your API token is now configured and ready to use!

### Accessing NSFW Content (Optional)

To download NSFW (Not Safe For Work) models, you'll need OAuth authentication. Regular API tokens cannot access NSFW content.

#### Setup Steps

1. **Get Your OAuth Credentials**
   - Go to [https://www.thingiverse.com/apps/](https://www.thingiverse.com/apps/)
   - Note your **Client ID** and **Client Secret**
   - Ensure **Redirect URI** is set to: `http://localhost:8080/callback`

2. **Configure Environment Variables**
   - Create a `.env` file in the project directory:
     ```
     THINGIVERSE_CLIENT_ID=your_client_id_here
     THINGIVERSE_CLIENT_SECRET=your_client_secret_here
     ```
   - Or set them as system environment variables

3. **Run with --nsfw Flag**
   - A browser window will open for you to log in and authorize
   - The script automatically captures your authentication token
   - Only models marked as NSFW will be downloaded

#### Example Usage

```bash
python thingiscrape.py --search "nsfw" --nsfw True --pages 1
```

#### How It Works

- The `--nsfw True` flag enables OAuth authentication and filters results
- **Only downloads models where `is_nsfw: true`** in the API response
- Automatically skips non-NSFW models during download
- You can search for any keywords; the NSFW filter ensures only adult content is downloaded

## Regular usage 

To see the various options available to you type the following into your terminal.

```
python thingiscrape.py --help
```

Example usage:

```
python thingiscrape.py --search "yoda" --popular 1 --pages 2 --license "cc"
```

STL 3D model files will be downloaded to `./downloads/stls/` along with a json file containing the results from the request in `./downloads/json/`.

## Usage

To see the various options available to you type the following into your terminal.

```
python thingiscrape.py --help
```

Example usage:

```
python thingiscrape.py --search "yoda" --popular 1 --pages 2 --license "cc"
```

STL 3D model files will be downloaded to `./downloads/stls/` along with a json file containing the results from the request in `./downloads/json/`.
