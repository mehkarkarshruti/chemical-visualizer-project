# **Chemical Equipment Parameter Visualizer**



##### Overview

Chemical Equipment Parameter Visualizer is a hybrid web + desktop application for analyzing chemical equipment data using CSV files.

It computes statistical summaries and visualizes parameters like flowrate, pressure, and temperature.

A single Django backend powers both the React web app and the PyQt5 desktop app, ensuring consistent behavior across platforms.



##### Features



CSV file upload and validation

Automatic statistical analysis

Interactive charts and dashboards

Web and desktop support

PDF report generation

Stores last 5 uploaded datasets



##### Tech Stack

Backend: Django, Django REST Framework

Web Frontend: React, Chart.js

Desktop App: PyQt5, Matplotlib

Data Processing: Pandas

Database: SQLite



##### How It Works



User uploads a CSV file

Backend processes and analyzes data

Statistics are calculated and stored

Results are displayed as charts and summaries

Reports can be generated as PDFs



###### Sample CSV Format



Equipment Name,Type,Flowrate,Pressure,Temperature

Reactor A,CSTR,150,2.5,85

Reactor B,PFR,200,3.2,90



###### Running the Project

*Backend*

cd backend

python manage.py runserver



*Web App*

cd frontend

npm install

npm start



*Desktop App*

python desktop\_app.py



##### Project Structure



chemical-equip-parameter-visualizer/

├── backend/

├── frontend/

├── desktop\_app/

└── README.md



##### Developer



**Shruti Mehkarkar**

VIT Bhopal University



Status:

Project completed and fully functional.

