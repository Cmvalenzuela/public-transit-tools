################################################################################
## Toolbox: Add GTFS to a Network Dataset / Transit Analysis Tools
## Tool name: Prepare Time Lapse Polygons
## Created by: Melinda Morang, Esri, mmorang@esri.com
## Last updated: 27 July 2017
################################################################################
'''Run a Service Area analysis incrementing the time of day. Save the polygons 
to a feature class that can be used to generate a time lapse video.'''
################################################################################
'''Copyright 2017 Esri
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.'''
################################################################################

import datetime
import arcpy
import AnalysisHelpers
arcpy.env.overwriteOutput = True

class CustomError(Exception):
    pass

try:

    #Check out the Network Analyst extension license
    if arcpy.CheckExtension("Network") == "Available":
        arcpy.CheckOutExtension("Network")
    else:
        arcpy.AddError("You must have a Network Analyst license to use this tool.")
        raise CustomError


    # ----- Get and process inputs -----

    # Service Area from the map that is ready to solve with all the desired settings
    # (except time of day - we'll adjust that in this script)
    input_network_analyst_layer = arcpy.GetParameter(0)
    desc = arcpy.Describe(input_network_analyst_layer)
    if desc.dataType != "NALayer" or desc.solverName != "Service Area Solver":
        arcpy.AddError("Input layer must be a Service Area layer.")
        raise CustomError
    
    # Output feature class of SA polygons which can be used to make a time lapse
    # End result will have a time field indicating which time of day the polygon is for
    output_feature_class = arcpy.GetParameterAsText(1)

    # Start and end day and time
    start_day_input = arcpy.GetParameterAsText(2)
    end_day_input = arcpy.GetParameterAsText(4)
    start_time_input = arcpy.GetParameterAsText(3)
    end_time_input = arcpy.GetParameterAsText(5)
    increment_input = arcpy.GetParameter(6)

    # Make list of times of day to run the analysis
    timelist = AnalysisHelpers.make_analysis_time_of_day_list(start_day_input, end_day_input, start_time_input, end_time_input, increment_input)

    
    # ----- Add a TimeOfDay field to SA Polygons -----

    # Grab the polygons sublayer, which we will export after each solve.
    sublayer_names = arcpy.na.GetNAClassNames(input_network_analyst_layer) # To ensure compatibility with localized software
    polygons_subLayer = arcpy.mapping.ListLayers(input_network_analyst_layer, sublayer_names["SAPolygons"])[0]

    time_field = "TimeOfDay"

    # Clean up any pre-existing fields with this name (unlikely case)
    poly_fields = arcpy.ListFields(polygons_subLayer, time_field)
    if poly_fields:
        for f in poly_fields:
            if f.name == time_field and f.type != "Date":
                arcpy.AddWarning("Your Service Area layer's Polygons sublayer contained a field called TimeOfDay \
of a type other than Date.  This field will be deleted and replaced with a field of type Date used for the output \
of this tool.")
                arcpy.management.DeleteField(polygons_subLayer, time_field)

    # Add the TimeOfDay field to the Polygons sublayer.  If it already exists, this will do nothing.
    arcpy.na.AddFieldToAnalysisLayer(input_network_analyst_layer, sublayer_names["SAPolygons"], time_field, "DATE")


    # ----- Solve NA layer in a loop for each time of day -----

    # Grab the solver properties object from the NA layer so we can set the time of day
    solverProps = arcpy.na.GetSolverProperties(input_network_analyst_layer)

    # Solve for each time of day and save output
    arcpy.AddMessage("Solving Service Area at time...")
    for t in timelist:
        arcpy.AddMessage(str(t))
        
        # Switch the time of day
        solverProps.timeOfDay = t
        
        # Solve the Service Area
        arcpy.na.Solve(input_network_analyst_layer)
        
        # Calculate the TimeOfDay field
        expression = '"' + str(t) + '"' # Unclear why a DATE field requires a string expression, but it does.
        arcpy.management.CalculateField(polygons_subLayer, time_field, expression, "PYTHON_9.3")
        
        #Append the polygons to the output feature class. If this was the first
        #solve, create the feature class.
        if not arcpy.Exists(output_feature_class):
            arcpy.management.CopyFeatures(polygons_subLayer, output_feature_class)
        else:
            arcpy.management.Append(polygons_subLayer, output_feature_class)

except CustomError:
    pass
except:
    raise
