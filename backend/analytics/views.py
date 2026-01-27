from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import CSVUploadSerializer
import pandas as pd

# Global variable to store the last summary
last_summary = None

class UploadCSV(APIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = CSVUploadSerializer

    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data['file']
        df = pd.read_csv(file)

        summary = {
            "total_equipment": len(df),
            "avg_flowrate": df["Flowrate"].mean(),
            "avg_pressure": df["Pressure"].mean(),
            "avg_temperature": df["Temperature"].mean(),
            "type_distribution": df["Type"].value_counts().to_dict()
        }

        # Save summary globally so GET can access it
        global last_summary
        last_summary = summary

        return Response(summary)


class SummaryView(APIView):
    def get(self, request):
        global last_summary
        if last_summary:
            return Response(last_summary)
        else:
            return Response({"detail": "No summary available. Please upload a CSV first."})