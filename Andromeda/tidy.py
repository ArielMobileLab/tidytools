import pandas as pd
import haversine as hs
import numpy as np
import statistics
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import itertools
import scipy.signal as sp

## ---------------------------------------------------------------------------
def filter_acceleration(x):
    high_pass_window=600
    x=x-x.rolling(window=high_pass_window,center=True,min_periods=1).median() ## highpass 
    low_pass_window=10
    x=x.rolling(window=low_pass_window,center=True,min_periods=1).mean()
    x=x-statistics.median(x)
    return x

def filter_real_time_acceleration(x):
    high_pass_window=600
    x=x.rolling(window=7,center=True,min_periods=1).median() ## highpass 
    x=x.rolling(window=20,center=True,min_periods=1).mean()
    return x

def Distance_Driven_haversine(Latitude,Longitude,):
    n=len(Latitude)
    Distance_Driven = [0] * n
    for i in np.arange(n-1):
        loc1=(Latitude[i],Longitude[i])
        loc2=(Latitude[i+1],Longitude[i+1])
        Distance_Driven[i+1] = hs.haversine(loc1,loc2,unit='m')
    Distance_Driven = np.cumsum(Distance_Driven)
    return Distance_Driven

#Calculate the distance (in different units) between two points on the earth using their latitude and longitude.
def distanceHaversinePoints(p1_lat,p1_lng,p2_lat,p2_lng):
    loc1=(p1_lat,p1_lng)
    loc2=(p2_lat,p2_lng)
    return hs.haversine(loc1,loc2,unit='m')
                
def distanceHaversineVectors(p1_lat,p1_lng,p2_lat,p2_lng):
    distance=[]
    for i in np.arange(len(p1_lat)):
        dis=distanceHaversinePoints(p1_lat[i],p1_lng[i],p2_lat[i],p2_lng[i])
        distance.append(dis)
    return distance

def tidy_cognata(path):
    df=pd.read_json(path)
    df = (pd.DataFrame(df['Logs'].values.tolist()).join(df.drop('Logs', 1)))
    df=pd.DataFrame.from_dict(df, orient='columns')
    fixedTime = df.WorldTime[0]
    fixedTime2 = fixedTime[0:15]
    try:
        fixedTime3 = datetime.strptime(fixedTime2, "%H:%M:%S.%f")
    except:
        fixedTime3 = datetime.strptime(fixedTime2+".0", "%H:%M:%S.%f")
    for x in df.index:
        currentTime = df.WorldTime[x]
        currentTime2 = currentTime[0:15]
        try:
            currentTime3 = datetime.strptime(currentTime2, "%H:%M:%S.%f")
        except:
            currentTime3 = datetime.strptime(currentTime2+".0", "%H:%M:%S.%f")
        delta = currentTime3 - fixedTime3
        deltasec = delta.total_seconds()
        #df.RealTime[x] = deltasec
    ### Termination
    Termination=df[df.Type=='Termination']
    if len(Termination)>0:
        Termination=Termination[['SimulationTime','Reason']]
    else:
        Termination=pd.DataFrame({
            'SimulationTime':   [max(df['SimulationTime'])], 
            'Reason'        :   ['No termination data']})

    ### Begining
    Begining=pd.DataFrame({
                'SimulationTime':   [min(df['SimulationTime'])], 
                'Reason'        :   ['Start']})
    Termination=Termination.append(Begining)
                
    ### Merge outer join
    df = pd.merge(df, Termination, on='SimulationTime', how='outer')

    return df
         
def tidy_engine(path):
    try:
        #path=r'H:\\My Drive\\Ariel Uni\\B1_582444\\Simulation\\5.AVATAR\\Color\\EgoCar_Color_2024-01-22_14-59-52.json'
      
        df=pd.read_json(path)
        df=pd.json_normalize(df['Logs'])
        


       
### GPS messages
        GPS=df[df.Type=='GPS']
        GPS=GPS.dropna(axis=1, how='all')
        GPS=GPS.drop(['Type'], axis=1)
        GPS["ForwaredAcceleration"]=999.99
        GPS["LateralAcceleration"]=999.99
        GPS["UpwardAcceleration"]=999.99
        GPS["ForwaredAccelerationRow"]=999.99
        GPS["LateralAccelerationRow"]=999.99
        GPS["UpwardAccelerationRow"]=999.99
        GPS["ForwaredAccelerationFilter"]=999.99
        for i in np.arange(len(GPS["Acceleration.y"])):     
            GPS["ForwaredAccelerationFilter"].iloc[i]=GPS["ForwaredAccelerationRow"].iloc[i]=GPS["ForwaredAcceleration"].iloc[i]=float(GPS["Acceleration.x"].iloc[i])
            GPS["LateralAccelerationRow"].iloc[i]=GPS["LateralAcceleration"].iloc[i]=float(GPS["Acceleration.y"].iloc[i])
            GPS["UpwardAccelerationRow"].iloc[i]=GPS["UpwardAcceleration"].iloc[i]=float(GPS["Acceleration.z"].iloc[i])
     
            
        GPS=GPS.reset_index()
        GPS["RealTime"] = " "
        GPS["Distance_Driven"]=Distance_Driven_haversine(GPS['Latitude'],GPS['Longitude'])
        
        fixedTime = GPS.WorldTime[0]
        fixedTime2 = fixedTime[0:15]
        try:
            fixedTime3 = datetime.strptime(fixedTime2, "%H:%M:%S.%f")
        except:
            fixedTime3 = datetime.strptime(fixedTime2+".0", "%H:%M:%S.%f")
        for x in GPS.index:
            currentTime = GPS.WorldTime[x]
            currentTime2 = currentTime[0:15]
            try:
                currentTime3 = datetime.strptime(currentTime2, "%H:%M:%S.%f")
            except:
                currentTime3 = datetime.strptime(currentTime2+".0", "%H:%M:%S.%f")
            delta = currentTime3 - fixedTime3
            deltasec = delta.total_seconds()
            GPS.RealTime[x] = deltasec
            
        GPS['CumulativeSpeed']=np.cumsum(GPS.Speed)
        GPS['CumulativeSpeedPWR2']=np.cumsum(GPS.Speed**2)
        GPS['Samples']=np.arange(len(GPS))+1
        

### CarTelemetries messages
        if (sum(df.Type=='CarTelemetries')):
            CarTelemetries=df[df.Type=='CarTelemetries']
            CarTelemetries=CarTelemetries.dropna(axis=1, how='all')
            ### Sometimes have raws with the same frame ID. Take only the first one
            CarTelemetries = CarTelemetries.sort_values('FrameID').drop_duplicates('FrameID', keep='first')  
            CarTelemetries = CarTelemetries.reset_index(drop=True)
            if "Gear" in CarTelemetries:
                CarTelemetries["Gear"] = CarTelemetries["Gear"].ffill().astype(np.int64)
          
            CarTelemetries.Acceleration=pd.to_numeric(CarTelemetries.Acceleration)
            CarTelemetries["Longitudinal_Acceleration"]=pd.to_numeric(CarTelemetries.Acceleration)
            thisFilter = CarTelemetries.filter(['Type', 'WorldTime', 'FrameID', 'Speed','Acceleration'])
            CarTelemetries=CarTelemetries.drop(thisFilter, axis=1,errors='ignore')
           
            df_wide = pd.merge(GPS, CarTelemetries, on='SimulationTime', how='outer')
           
        else:
            df_wide=GPS
        
        if "Gear" in df_wide.columns:
            df_wide["Gear"] = df_wide["Gear"].ffill().fillna(0).astype(np.int64)
        # The filtered acceleration while later be used to identify kinematic events
        if ("Gear" in df_wide.columns and sum(df_wide["Gear"])>0):  
               df_wide["ForwaredAccelerationFilter"]=sp.medfilt(df_wide["ForwaredAccelerationFilter"],7)
               GearChangeFrames=df_wide.loc[df_wide.Gear.diff().isin([-2,-1]),'FrameID']
               for f in GearChangeFrames: 
                   df_wide.loc[(df_wide.FrameID>=f) & (df_wide.FrameID<=f+50),"ForwaredAccelerationFilter"]=np.NAN        
               df_wide["ForwaredAccelerationFilter"]=df_wide["ForwaredAccelerationFilter"].interpolate(method='linear')
   
        df_wide["ForwaredAcceleration"]=filter_acceleration(df_wide["ForwaredAccelerationFilter"])
        df_wide["LateralAcceleration"]=filter_acceleration(df_wide["LateralAcceleration"])
        df_wide["UpwardAcceleration"]=filter_acceleration(df_wide["UpwardAcceleration"])

        df_wide["ForwaredAccelerationCarla"]=filter_real_time_acceleration(df_wide["ForwaredAccelerationRow"])
        
        
### Termination
        Termination=df[df.Type=='Termination']
        if len(Termination)>0:
             Termination=Termination[['SimulationTime','Reason']]
             Termination['Reason']=[element.replace('Crash', 'collided') for element in Termination['Reason']]
            #Termination=Termination.drop(['Type', 'WorldTime', 'FrameID','Speed','Distance_Driven'], axis=1)
        else:
            Termination=pd.DataFrame({
                    'SimulationTime':   [max(GPS['SimulationTime'])], 
                    'Reason'        :   ['No termination data']})

### Begining
        Begining=pd.DataFrame({
            'SimulationTime':   [min(GPS['SimulationTime'])], 
            'Reason'        :   ['Start']})
        Termination=pd.concat([Termination,Begining])
        

### Merge outer join
        df_wide = pd.merge(df_wide, Termination, on='SimulationTime', how='outer')
        df_wide[['WorldTime','Samples','Distance_Driven','RealTime']] = df_wide[['WorldTime','Samples','Distance_Driven','RealTime']].ffill()

        #df_wide = df_wide[df_wide['FrameID'].isna()==False]
    except:
        return None
    return df_wide
    
def tidy_gps(path):  # load json to gsp df
    try:
        df=pd.read_json(path)
        df=pd.json_normalize(df['Logs'])
        df = df[df['Name'].isin(['Lead Vehicle', 'lead car','carinfront'])].reset_index()     
        
        df["ForwaredAcceleration"]=999.99
        df["LateralAcceleration"]=999.99
        df["UpwardAcceleration"]=999.99
        for i in np.arange(len(df["Acceleration.y"])):     
           df["ForwaredAcceleration"].iloc[i]=float(df["Acceleration.x"].iloc[i])
           df["LateralAcceleration"].iloc[i]=float(df["Acceleration.y"].iloc[i])
           df["UpwardAcceleration"].iloc[i]=float(df["Acceleration.z"].iloc[i])
       
       # The filtered acceleration while later be used to identify kinematic events
        df["ForwaredAcceleration"]=filter_acceleration(df["ForwaredAcceleration"])
        df["LateralAcceleration"]=filter_acceleration(df["LateralAcceleration"])
        df["UpwardAcceleration"]=filter_acceleration(df["UpwardAcceleration"])
       
        df=df.reset_index()
        df["RealTime"] = " "
        df["Distance_Driven"]=Distance_Driven_haversine(df['Latitude'],df['Longitude'])
        fixedTime = df.WorldTime[0]
        fixedTime2 = fixedTime[0:15]
        fixedTime3 = datetime.strptime(fixedTime2, "%H:%M:%S.%f")
        for x in df.index:
            currentTime = df.WorldTime[x]
            currentTime2 = currentTime[0:15]
            currentTime3 = datetime.strptime(currentTime2, "%H:%M:%S.%f")

            delta = currentTime3 - fixedTime3
            deltasec = delta.total_seconds()
            df.RealTime[x] = deltasec
            
        df = df[['SimulationTime', 'Latitude', 'Longitude','RealTime','WorldTime','Speed','ForwaredAcceleration','LateralAcceleration','Name','Distance_Driven']] 
        
        ### Termination
        Termination=pd.DataFrame({
            'SimulationTime':   [max(df['SimulationTime'])], 
            'Reason'        :   ['No termination data']})

### Begining
        Begining=pd.DataFrame({
            'SimulationTime':   [min(df['SimulationTime'])], 
            'Reason'        :   ['Start Simulation']})
        Termination=pd.concat([Termination,Begining])

### miscellaneous 
     #   df['Distance_Driven']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeSpeed']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['Samples']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeSpeedPWR2']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeDistanceToLead']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeDistanceToLeadPWR2']=None 
        df = pd.merge(df, Termination, on='SimulationTime', how='outer')

    except:
        return None
    return df
    
def tidy_carla_objects(path): 
    try:
        df=pd.read_json(path)
        df=pd.json_normalize(df['Logs'])
        df=df.rename(columns={"longitude": "Longitude", "latitude": "Latitude", "altitude": "Altitude"})
        df=df[df['Name'].notnull()]
        df = df[df['Name'].str.contains("vehicle.tesla.model3")]
        df=df.sort_values(by=['Name','SimulationTime'])
       
        df=df.reset_index()
        df["RealTime"] = " "
        df["Distance_Driven"]=Distance_Driven_haversine(np.float64(df['Latitude']),np.float64(df['Longitude']))
        for V in df.Name.unique():
            min_distance=min(df.loc[df.Name==V,"Distance_Driven"])
            df.loc[df.Name==V,"Distance_Driven"]=df.loc[df.Name==V,"Distance_Driven"]-min_distance
        df[['Name','Distance_Driven']].groupby(['Name']).max() 
        fixedTime = df.WorldTime[0]
        fixedTime2 = fixedTime[0:15]
        fixedTime3 = datetime.strptime(fixedTime2, "%H:%M:%S.%f")
        for x in df.index:
            currentTime = df.WorldTime[x]
            currentTime2 = currentTime[0:15]
            currentTime3 = datetime.strptime(currentTime2, "%H:%M:%S.%f")

            delta = currentTime3 - fixedTime3
            deltasec = delta.total_seconds()
            df.RealTime[x] = deltasec
        
        for V in df.Name.unique():
            min_RealTime=min(df.loc[df.Name==V,"RealTime"])
            df.loc[df.Name==V,"RealTime"]=df.loc[df.Name==V,"RealTime"]-min_RealTime
           
            
        df = df[['SimulationTime', 'Latitude', 'Longitude','RealTime','WorldTime','Speed','Name','Distance_Driven']] 
        
        ### Termination
        Termination=pd.DataFrame({
            'SimulationTime':   [max(df['SimulationTime'])], 
            'Reason'        :   ['No termination data']})

### Begining
        Begining=pd.DataFrame({
            'SimulationTime':   [min(df['SimulationTime'])], 
            'Reason'        :   ['Start Simulation']})
        Termination=pd.concat([Termination,Begining])

### miscellaneous 
     #   df['Distance_Driven']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeSpeed']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['Samples']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeSpeedPWR2']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeDistanceToLead']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeDistanceToLeadPWR2']=None 
        df = pd.merge(df, Termination, on='SimulationTime', how='outer')

    except:
        return None
    return df
    
def tidy_teleoperation(path):
    df = pd.read_excel(path)
    if (len(df)>0):
        df=df.rename(columns = {'measurement time':'measurement_time'})
        df=df.rename(columns = {'Pose.Position.X':'Latitude'})
        df=df.rename(columns = {'Pose.Position.Y':'Longitude'})
        df=df.rename(columns = {'Pose.Orientation.X':'Pose_Orientation_X'})
        df=df.rename(columns = {'Pose.Orientation.Y':'Pose_Orientation_Y'})
        df=df.rename(columns = {'Velocity.Linear.X':'Speed'})
        df=df.rename(columns = {'Velocity.Linear.Y':'Velocity_Linear_Y'})
        df=df.rename(columns = {'Accel.Linear.X':'ForwaredAcceleration'})
        df=df.rename(columns = {'Accel.Linear.Y':'LateralAcceleration'})
        df=df.rename(columns = {'Accel.Linear.Z':'UpwardAcceleration'})
        
        # The filtered acceleration while later be used to identify kinematic events
        df["ForwaredAcceleration"]=df["ForwaredAcceleration"].rolling(128,center=True,min_periods=1).mean()
        df["LateralAcceleration"]=df["LateralAcceleration"].rolling(128,center=True,min_periods=1).mean()
        df["UpwardAcceleration"]=df["UpwardAcceleration"].rolling(128,center=True,min_periods=1).mean()
        
        Distance_Driven = (np.diff(df.Latitude)**2 + np.diff(df.Longitude)**2)**0.5
        Distance_Driven = np.pad(Distance_Driven, (1, 0), 'constant', constant_values=(0))
        Distance_Driven = np.cumsum(Distance_Driven)
        df['Distance_Driven']=Distance_Driven ## It is the same name as in the simulator files
        df['CumulativeSpeed']=np.cumsum(df.Speed)
        df['CumulativeSpeedPWR2']=np.cumsum(df.Speed**2)
        df['Samples']=np.arange(len(df))+1
        df['SimulationTime']= df['measurement_time'] ##For allignment with cognata files
        df['RealTime']= df['measurement_time'] ##For allignment with cognata files
        ##For allignment with cognata files
        if 'Time-H' in df.columns:
            df_time = pd.DataFrame({
                'year': list(itertools.repeat(2021, len(df))),
                'month':list(itertools.repeat(1, len(df))),
                'day': list(itertools.repeat(1, len(df))),
                'hour': df['Time-H'],
                'minute': df['Time-M'],
                'second': np.floor(df['Time-S']),
                'ms': (df['Time-S']-np.floor(df['Time-S']))*1000})

            df['WorldTime']= pd.to_datetime(df_time)
        if 'GPS.Time' in df.columns: ### Check with Alex if this conversion is correct
             df['WorldTime']=datetime(2024, 7, 22) + pd.TimedeltaIndex(df['GPS.Time']*0.0007+4*60*60,unit='s')
                ### Termination
        Termination=pd.DataFrame({
            'SimulationTime':   [max(df['SimulationTime'])], 
            'Reason'        :   ['No termination data']})

### Begining
        Begining=pd.DataFrame({
            'SimulationTime':   [min(df['SimulationTime'])], 
            'Reason'        :   ['Start Simulation']})
        Termination=pd.concat([Termination,Begining])

### miscellaneous 
        df['CumulativeDistanceToLead']=None    ## currently we don't need the Distance_Driven the columns is added for
        df['CumulativeDistanceToLeadPWR2']=None 
        df = pd.merge(df, Termination, on='SimulationTime', how='outer')

    return df
def tidy_carla(path):
    #path=r'H:\My Drive\Ariel Uni\B5_580571\Simulation\5.AVATAR\Color\EgoCar_Color_2024-01-16_15-33-54.json'
    try:
        #path=r"G:\My Drive\Ariel Uni\A1_012594\Simulator\4.Latency\Latency3\7081(11 20 29)-CognataEngineLog (9).JSON"
        df=pd.read_json(path, lines=True)
        # df = (pd.DataFrame(df['Logs'].values.tolist()).join(df.drop('Logs', 1)))
        # df=pd.DataFrame.from_dict(df, orient='columns')
        df = df.rename(columns={"Reson": "Reason"})
        df = df.rename(columns={"Simulation_time": "SimulationTime"})
        df["WorldTime"]=df["Timestamp"].astype(str).str.slice(11,19)


### GPS messages
        GPS=df[df.Type=="Ego car Sensors:"]
        GPS=GPS.dropna(axis=1, how='all')
        GPS=GPS.drop(['Type'], axis=1)
        GPS["ForwaredAcceleration"]=999.99
        GPS["LateralAcceleration"]=999.99
        GPS["UpwardAcceleration"]=999.99
        GPS["ForwaredAcceleration"]=GPS.Acceleration_x
        GPS["LateralAcceleration"]=GPS.Acceleration_y
        GPS["UpwardAcceleration"]=GPS.Acceleration_z    
        # The filtered acceleration while later be used to identify kinematic events
        GPS["ForwaredAcceleration"]=filter_acceleration(GPS["ForwaredAcceleration"])
        GPS["LateralAcceleration"]=filter_acceleration(GPS["LateralAcceleration"])
        GPS["UpwardAcceleration"]=filter_acceleration(GPS["UpwardAcceleration"])
        
        GPS=GPS.reset_index()
        GPS["RealTime"] = df["SimulationTime"]
        GPS["Distance_Driven"]=Distance_Driven_haversine(GPS['Latitude'],GPS['Longitude'])
        GPS['CumulativeSpeed']=np.cumsum(GPS.Speed)
        GPS['CumulativeSpeedPWR2']=np.cumsum(GPS.Speed**2)
        GPS['Samples']=np.arange(len(GPS))+1
        GPS["Longitudinal_Acceleration"]=GPS["ForwaredAcceleration"]
### Termination
        Termination=df[df.Type=='Termination:']
        if len(Termination)==0:   
            Termination=pd.DataFrame({
                    'SimulationTime':   [max(GPS['SimulationTime'])], 
                    'Reason'        :   ['No termination data']})
        Termination=Termination[['SimulationTime','Reason']]

### Begining
        Begining=pd.DataFrame({
            'SimulationTime':   [min(GPS['SimulationTime'])], 
            'Reason'        :   ['Start']})
        Termination=pd.concat([Termination,Begining])
        
### Merge outer join
        df = pd.merge(GPS, Termination, on='SimulationTime', how='outer')
    except:
        return None
    return df

def tidy_feedback(path):
    #path=r'H:\My Drive\Ariel Uni\B1_582444\Simulation\5.AVATAR\Color\Face_StatusColor_2024-01-22_14-59-52.json'
    try:
        df=pd.read_json(path, lines=True)
        # df = (pd.DataFrame(df['Logs'].values.tolist()).join(df.drop('Logs', 1)))
        # df=pd.DataFrame.from_dict(df, orient='columns')
        df = df.rename(columns={"Simulation_time": "SimulationTime"})
        df["WorldTime"]=df["Timestamp"].astype(str).str.slice(11,19)
        
        df.loc[df['Type']=="Face_Status:",'Type']='Face_Status'
        df=df.rename(columns={"Face_State":"Event_ID"})
        df['Event_Name']=None
        df.loc[df.Event_ID==2,'Event_Name']='PositiveFeedback'
        df.loc[df.Event_ID==3,'Event_Name']='NegativeFeedback'   
    except:
        return None
    return df

# =============================================================================
# Internals
# =============================================================================
def signal_zerocrossings(signal, direction="both"):
    df = np.diff(np.sign(signal))
    if direction in ["positive", "up"]:
        zerocrossings = np.where(df > 0)[0]
    elif direction in ["negative", "down"]:
        zerocrossings = np.where(df < 0)[0]
    else:
        zerocrossings = np.nonzero(np.abs(df) > 0)[0]

    return zerocrossings

def findpeaks(x,thresh=0.2):
    peaks_list = []
    onsets_list = []
    ends_list= []
    amps_list = []
    
    # zero crossings
    pos_crossings = signal_zerocrossings(x-thresh, direction="positive")
    neg_crossings = signal_zerocrossings(x-thresh, direction="negative")
    if len(pos_crossings)>0 and len(neg_crossings)>0:
        neg_crossings = neg_crossings[neg_crossings>min(pos_crossings)]
    # Sanitize consecutive crossings
        if len(pos_crossings) > len(neg_crossings):
            pos_crossings = pos_crossings[0:len(neg_crossings)]
        elif len(pos_crossings) < len(neg_crossings):
            neg_crossings = neg_crossings[0:len(pos_crossings)]

        for i, j in zip(pos_crossings, neg_crossings):
            if j>i:
                window = x[i:j]
                amp = np.max(window)
                peak = np.arange(i,j)[window == amp][0]
                peaks_list.append(peak)
                onsets_list.append(i)
                amps_list.append(amp)
                ends_list.append(j)
            
    # output
        info = {"Onsets": np.array(onsets_list),
                "Peaks": np.array(peaks_list),
                "Amplitude": np.array(amps_list),
                "Ends": np.array(ends_list)}
        return info
    return None

### find the simulation time most near to a point
## The data must have the columns: lng & lat
def distance_to_point(data,point_lat,point_lng, dist_function="haversine"):
    if dist_function=="haversine":
        loc1=(point_lat,point_lng)
        loc2=(data['lat'],data['lng']) 
        rep=hs.haversine(loc1,loc2,unit='m')
    else:
        rep=((data['lng']-point_lng)**2+(data['lat']-point_lat)**2)**0.5
    return rep

def find_the_time_most_reasnable_for_point(lat,lng,time,point_lat,point_lng,distance_function="haversine"): 
    df = pd.DataFrame({'lat': lat,'lng': lng,'time': time}) 
    epsilon=0.00005
    v=(df.lat>point_lat-epsilon) & (df.lat<point_lat+epsilon) & (df.lng>point_lng-epsilon) & (df.lng<point_lng+epsilon)
    if np.sum(v)==0:
        return None
    df=df[v]
    if (df.time.max()-df.time.min())>30: ## more than 30 seconds in the event is not reasnable when driving.
        return None
    df.insert(0,'distance',df.apply(distance_to_point,args=(point_lat,point_lng,distance_function),axis=1))
    estimated_time=np.average(df.time, weights=1/pow(df.distance,4))
    return estimated_time

def find_the_time_most_reasnable_for_point_v2(lat,lng,time,point_lat,point_lng,event_number=1,distance_function="euclidean"): 
    
    # lat=df_wide.Latitude
    # lng=df_wide.Longitude
    # time=df_wide.SimulationTime
    # point_lat=subset.Latitude[index]
    # point_lng=subset.Longitude[index]
    # event_number=subset.Arrivel_Number[index]
    # distance_function=subset.Distance_Function[index]
    
    estimated_time=None
    columns = ["lat", "lng", "time"]
    a=np.array([lat,lng,time]) 
    a=a.transpose()
    df = pd.DataFrame(a,columns=columns) 
    df.insert(0,'distance',df.apply(distance_to_point,args=(point_lat,point_lng,distance_function),axis=1))
    picks=findpeaks(1/df.distance,thresh=1/5.5) ##1/devided by threshold distance so short distance will translate to a large number
    picks=pd.DataFrame(picks)
    if len(picks)>=event_number:
        picks=picks.loc[event_number-1]
        df_event=df.loc[picks["Onsets"]:picks["Ends"]]
        estimated_time=np.average(df_event.time, weights=1/pow(df_event.distance,4))
    return estimated_time
