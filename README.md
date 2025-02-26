# The Point of This

- Enable easy prototyping.
  - Less boilerplate, more features.
- Prevent new devs from rebuilding the wheel.
- A collection of dev/cs tools for on-demand tasks before they're integrated.

# Things Everyone Would Need

## Python Environment

```bash
brew install --cask miniconda
```

Use the command pallette to create a new conda environment.

```bash
conda activate ./.conda
conda install ipykernel
pip install -r requirements.txt
```

## Mongodb
[Install MongoDB on macOS](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/)

Change the MongoDB port from `27017` to `27018` in `/opt/homebrew/etc/mongod.conf` (for Apple Silicon Macs) to avoid conflicts with `botchan-ai-backend`.

## Getting Credentials

```bash
cp env.example .env
```

- MongoDB: Ask our admin.
- Azure AI Search: [Azure Portal](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/CognitiveSearch)
- AOAI Keys: [Azure AI](https://ai.azure.com/resource/overview?wsid=/subscriptions/a33bf290-a59d-49e8-94c3-d8b7f0f9a066/resourceGroups/wevnal-openai-playground/providers/Microsoft.CognitiveServices/accounts/wevnal-openai-playground2)


# Creating A Project

```bash
./new.sh proj_name
```
- Use `gsdf` to view data/output in a spreadsheet.
- Move reusable code to the `ut` folder.
- Notebooks should "run all" with credentials set up correctly.
- Place parameters at the top.

## New Feature

- Prototype locally in your notebook.
- Once it works, hand it to the backend team for integration.


## CS Tools

- Develop locally with `gsdf` and deploy to Google Drive.
- Ensure it works on Colab too.
- Automate setup much as possible.

## Dev Tools / Investigation / One-off Scripts

![RTFM](https://imgs.xkcd.com/comics/rtfm.png)  
*don't be like this*

- DO NOT push anything that writes to production *by default.*
  - Create a "dry mode".
- Minimize waiting with parallelization.

# Optionals

## Set Up Chromedriver for Selenium on Mac

```bash
brew install chromedriver
```

Mac will block you after installation/update, but you can allow it with these easy six steps!
1. `"chromedriver" Not Opened` dialog will pop up.
2. Click on the question mark.
3. Open Privacy & Security.
4. Click `done` on the original dialog.
5. In Privacy & Security, scroll down, click `Allow Anyway` for chromedriver.
6. Run your code again, click `Allow Anyway`.

## Set Up Ngrok

TODO
