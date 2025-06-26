# Creating Amplify Deployment Zip

## The build is complete! Now create the zip file:

### On Windows (PowerShell):

1. Open PowerShell in the frontend directory
2. Run these commands:

```powershell
# Navigate to frontend directory
cd C:\Users\harsh\OneDrive\Desktop\oncall\oncall-agent\frontend

# Create zip of .next folder
Compress-Archive -Path .\.next\* -DestinationPath amplify-deploy.zip -Force
```

### What to Upload:

1. Go to AWS Amplify Console: https://ap-south-1.console.aws.amazon.com/amplify/home?region=ap-south-1#/dwrjpz4zjwnql
2. Click on "main" branch
3. Click "Upload"
4. Upload the `amplify-deploy.zip` file
5. Deploy

### Important Notes:

- The zip should contain the CONTENTS of the `.next` folder, not the folder itself
- The build has already been completed successfully
- All static files and server components are ready

### After Upload:

Your app will be available at:
- https://main.dwrjpz4zjwnql.amplifyapp.com

### For Custom Domain:

After the deployment succeeds, you can add your custom domain `dreamops.pointblank.club` through the Amplify console.