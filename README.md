# Jamf Pro Offboard Utility

A cross-platform GUI tool designed to safely unmanage devices in Jamf Pro based on Advanced Search results. Supports macOS, iOS, iPadOS, and visionOS.

## Features
- Automatically detects if a search result is a Computer or a Mobile Device and applies the correct API logic.
- Export a text manifest of targeted devices before committing changes using the Dry Run (Export) button.
- Built-in API delay (0.2s) to prevent rate-limiting or server strain.
- Background threading prevents the app from freezing during large batches.

# How To Setup & Install

If running from macOS, you may want to create a venv to install the required python dependencies. Ensure you have **Python 3.10+** installed.
Once in the project directory with dependencies installed, you can run "python3 jamf_unmanager.py"
You could also create an .app with a command like "pyinstaller --noconsole --windowed --name "JamfOffboarder" jamf_unmanager.py"

## How to Use

Enter your Jamf Pro URL and account credentials. Note that this uses the Classic API, the account will need the following permissions:
Computers | Read,Update
Mobile Devices | Read,Update
Advanced Computer Searches | Read
Advanced Mobile Device Searches | Read
Users | Read | Optional, sometimes required if your advanced search uses user-based criteria

Additionally, depending on how Sites are utilized within Jamf, ensure Site Access for the user account is correct
