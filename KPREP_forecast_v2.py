# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os, sys, glob, re, pickle, time
import numpy as np
import scipy
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import urllib.request, urllib.error, urllib.parse
from KPREP_forecast_v2_tools import *
import xarray as xr
import pandas as pd
import datetime
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

## TODO
# Check for valid values of climate indices, if the timestap is updated does not indicate the value is updated..
## Fix causal hindcast

dt = datetime.date.today()
#date_list = [dt.year, dt.month, dt.day]
start0 = time.time()

predictands = ["GCEcom","20CRslp","GPCCcom"]
predictands = ["GCEcom"]
#predictands = ["GPCCcom"]

# Load these predictors, this does not mean that these are neceserally used.. see predictorz for those
predictors = ['CO2EQ','NINO34','PDO','AMO','IOD','CPREC','PERS','PERS_TREND']

# NAMELIST

## Resolution, currently only 25 or 50 is supported..
resolution = 1             # 1, 2.5 or 5.0

## Redo full hindcast period and remove original nc output file?
overwrite = False
## Redo a specific month / year?
overwrite_m = True          # Overwrite only the month specified with overw_m and overw_y
overw_m = 11                # Jan = 1, Feb = 2.. etc
overw_y = 2019

## Update indices if possible
UPDATE = True

## Save a figure with the correlation between predictors and predictand
PLOT_PREDCOR = True

##
VALIDATION = True           # Validates and makes figures of predicted values 

DYN_MONAVG = False          # Include the dynamical monthly averaging in the predictors
MLR_PRED = True             # Include the trend of the last 3 month as predictor

FORECAST = True             # Do forecast for given date?
HINDCAST = True             # Validate forecast based on hindcasts?
CROSVAL = True              # Use cross-validation for validation
CAUSAL = False              # Use causal method for validation
cv_years = 1                # Leave n out cross validation



## Validation period is 1961 - current

ens_size =      51
styear  =       1959    # Use data from this year until current
stvalyear =     1961    # Start validation from this year until previous year
endyear =       dt.year
endmonth =      dt.month-1  # -1 as numpy arrays start with 0

# Set working directories
bd = os.getcwd()+'/'
if bd == '/home/folmer/climexp/kprep/': # We're home
    bd_data = '/home/folmer/climexp_data/KPREPData/'
    bdid = bd_data+'inputdata/'
    bdp = bd+'plots/'
    bdnc = bd_data+'ncfiles/'
elif bd =='/data/climexp_data/kprep/': # We're on climate explorer
    bd_data = '/data/climexp_data/KPREPData/'
    bdid = bd_data+'inputdata/'
    bdp = bd+'plots/'
    bdnc = bd_data+'ncfiles/'
else: # we're in the test suite
    bd_data = '/home/folmer/climexp_data/KPREPData/'
    #bd_data = '/home/folmer/seclifirm_uea/ML/'
    bdid = bd_data+'inputdata/'
    bdp = bd+'plots/'
    bdnc = bd+'ncfiles/'
    

# Make directories if not already present
if not os.path.isfile(bd_data+'targetgrid'): os.system('mkdir -p '+bd_data+'targetgrid')
if not os.path.isfile(bdid): os.system('mkdir -p '+bdid)
if not os.path.isfile(bdp): os.system('mkdir -p '+bdp)
if not os.path.isfile(bdnc): os.system('mkdir -p '+bdnc)
if not os.path.isfile(bdnc+'cor_pred'): os.system('mkdir -p '+bdnc+'cor_pred')

# Defining some arrays used for writing labels and loading data
months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
monthzz = 'JFMAMJJASONDJFMAMJJASOND'

print('Data from Jan '+str(styear)+' up to '+str(months[dt.month-2])+' '+str(dt.year))

print('Predictands = ',predictands)
print('Predictors = ',predictors)
print('Horizontal resolution is ',str(resolution),' degrees')


# Create list of dates used
times = pd.date_range('{}-01'.format(styear),'{}-{}'.format(dt.year,str(dt.month).zfill(2)),freq='M')
#times = pd.date_range('1901-01',str(dt.year)+'-'+str(dt.month),freq='M')

# ************************************************************************
# Read in predictand data for fitting 
# ************************************************************************
start1 = time.time()
print('-- Read in predictand data for fitting --')
predictorz = []     # Predefine empty array, fill with specified predictors for predictand

#UPDATE_INDICES = check_updates2(inputdir=bdid) # if data can be update then returns TRUE
UPDATE_INDICES=False
if UPDATE_INDICES and UPDATE:
    import subprocess
    print("start updating monthly observations")
    subprocess.check_call(["./update_indices.sh",str(resolution)])
    print("done updating monthly observations")
    
for p,predictand in enumerate(predictands):
    
        
    if predictand == 'GISTEMP':
        print('not done yet..')
        
    
    elif predictand == 'GCEcom':
        ## These predictors are selelected for GCEcom in the first predictor selection step
        predictorz.append(['CO2EQ','NINO34','PDO','AMO','IOD','CPREC','PERS','PERS_TREND'])

        # Load data
        gcecom = xr.open_dataset('{}gcecom_r{}.nc'.format(bdid,resolution)).squeeze().sst.to_dataset()
        gcecom = gcecom.drop('lev')
        gcecom = gcecom.rename({'sst':'tas'})
      
        # Create mask where no data / sea ice / too many missing values etc.
        mask = np.sum((gcecom.tas.round(3) == 271.350),axis=0)>100. 
        if resolution == 2.5:
            mask[61:,:] = True
        elif resolution == 1.0:
            mask[156:,:] = True
        else:
            print('first check where to mask the data for Antarctica')
            sys.exit()
            
        
        # Create anomalies with 1980-2010 as baseline climatology
        
        hadcrucw = xr.open_dataset('{}had4_krig_v2_0_0_r{}.nc'.format(bdid,resolution)).squeeze().temperature_anomaly.to_dataset()
        hadcrucw = hadcrucw.rename({'temperature_anomaly':'tas'})
        #sys.exit()
        #hadcrucw = hadcrucw.drop('year')
        #hadcrucw = hadcrucw.drop('month')
        hadcrucw = hadcrucw.assign_coords(time = rewrite_time(hadcrucw)) # TODO, make this simpler..
        #sys.exit()
        # Create anomalies with 1980-2010 as baseline climatology
        #gcecom.tas.values = anom_df(gcecom.tas,1980,2010,1948)
        gcecom_anom = (gcecom.groupby('time.month') - gcecom.sel(time=slice('1980','2010')).groupby('time.month').mean('time')).drop('month')
        hadcrucw_anom = (hadcrucw.groupby('time.month') - hadcrucw.sel(time=slice('1980','2010')).groupby('time.month').mean('time')).drop('month')
        #hadcrucw.tas.values = anom_df(hadcrucw.tas,1980,2010,styear)
        #sys.exit()
        # Hadcrucw until 1979 and gcecom from 1980
        com = xr.concat([hadcrucw_anom.tas.sel(time=slice(None,'1999-12-01')),gcecom_anom.tas.sel(time=slice('2000-01-01',None))],dim='time')
        #com = xr.concat([hadcrucw.tas[:684,:],gcecom.tas[120:,:]],dim='time')
        #com.values[:,mask] = np.nan
        com = com.where(~mask)
        
        

        #com = com.rename('GCEcom')a
        if p == 0: predadata = xr.Dataset({'GCEcom':com.astype('float32')}) 
        else: predadata = xr.merge([predadata,com.astype('float32')])
        

    elif predictand == 'HadCRU4CW':
        # to do
        print('to do')

    elif predictand == 'GPCCcom':
        # These predictors are selelected for GPCCcom in the first predictor selection step
        predictorz.append(['CO2EQ','NINO34','PDO','AMO','IOD','PERS','PERS_TREND'])
        #gpcccom = xr.open_dataset(bdid+'gpcc_10_combined_r'+str(resolution)+'.nc').squeeze()
        gpcccom = xr.open_dataset('{}gpcc_10_combined_mon_r{}.nc'.format(bdid,resolution),decode_times=False).squeeze().precip.to_dataset()
        gpcccom = decode_timez(gpcccom)
        # Remove too much of the data
        gpcccom = gpcccom.dropna(dim='time',how='all')
        # Create anomalies with 1980-2010 as baseline climatology
        gpcccom_anom = (gpcccom.groupby('time.month') - gpcccom.sel(time=slice('1980','2010')).groupby('time.month').mean('time')).drop(['level','month'])
        #gpcccom.precip.values = anom_df(gpcccom.precip,1980,2010,styear)
        #gpcccom.time.values = rewrite_time(gpcccom)

        #gpcccom_anom = gpcccom_anom.precip.rename('GPCCcom')
        #if p == 0: predadata = xr.Dataset({'GPCCcom':gpcccom_anom.astype('float32')})
        if p == 0: predadata = gpcccom_anom.astype('float32').rename({'precip':'GPCCcom'})
        else: predadata = xr.merge([predadata,gpcccom_anom.astype('float32')]).rename({'precip':'GPCCcom'})


    elif predictand == '20CRslp':
        # These predictors are selelected for 20CRslp in the first predictor selection step
        predictorz.append(['CO2EQ','NINO34','PDO','AMO','IOD','CPREC','PERS','PERS_TREND'])
        slp = xr.open_dataset('{}slp_mon_mean_1901-current_r{}.nc'.format(bdid,resolution)).squeeze().rename({'prmsl':'20CRslp'})
        slp_anom = (slp.groupby('time.month') - slp.sel(time=slice('1980','2010')).groupby('time.month').mean('time')).drop('month')
        #slp.prmsl.values = anom_df(slp.prmsl,1980,2010,styear)
        #slp_anom = slp_anom.prmsl.rename('20CRslp')
        #slp.time.values = rewrite_time(slp)
        #if p == 0: predadata = xr.Dataset({'20CRslp':slp_anom.astype('float32')})
        if p == 0: predadata = slp_anom.astype('float32')
        else: predadata = xr.merge([predadata,slp_anom.astype('float32')])

    else:
        print('predictand not yet known.. exiting!')
        sys.exit()
#sys.exit()
 
print('-- Done reading in predictand data for fitting, time = ',str(np.int(time.time()-start1)),' seconds --') 



# ************************************************************************
# Read in predictor data for fitting 
# ************************************************************************
start1 = time.time()
print('-- Read in predictor data for fitting --')

indices_locs = {'CO2EQ':bdid+'RCP45_CO2EQ_mo.dat',
                'NINO34':bdid+'ersst_nino3.4a.dat',
                'QBO':bdid+'qbo?.dat',
                'IOD':bdid+'dmi_ersst.dat',
                'PDO':bdid+'pdo_ersst.dat',
                'AMO':bdid+'amo_ersst_ts.dat',
                'PERS':'not needed',
                'PERS_TREND':'not needed'}

# Load predictors (time,lat,lon)
for i,pred in enumerate(predictors):
    print(i,pred)
    if pred in ['PERS','PERS_TREND']:
        continue

    elif pred == 'CPREC':    # Cum precip [time,lat,lon] - 1901 -current
        if 'gpcccom_anom' not in locals():
            gpcccom = xr.open_dataset('{}gpcc_10_combined_mon_r{}.nc'.format(bdid,resolution),decode_times=False).squeeze().precip.to_dataset()
            gpcccom = decode_timez(gpcccom)
            # Remove too much of the data
            gpcccom = gpcccom.dropna(dim='time',how='all')
            # Create anomalies with 1980-2010 as baseline climatology
            gpcccom_anom = gpcccom.groupby('time.month') - gpcccom.sel(time=slice('1980','2010')).groupby('time.month').mean('time')
            
        if i == 0: 
            predodata = gpcccom_anom.rename({'precip':'CPREC'}).sel(time=slice('1901-01-01',None)).astype('float32')
        else:
            predodata = xr.merge([predodata,gpcccom_anom.rename({'precip':'CPREC'}).sel(time=slice('1901-01-01',None)).astype('float32')])            


    else:
        df = load_clim_index(indices_locs[pred],styear,endyear,endmonth,pred)
        print(df)
        if i==0: predodata = df
        else: predodata = xr.merge([predodata,df.astype('float32')])

        
print('-- Done reading in predictor data for fitting, time = ',str(np.int(time.time()-start1)),' seconds --') 
#sys.exit()

# Sanity check on predictor data..
for var in predodata:
    if predodata[var].isel(time=-1).max() < -900:
        print(var+' not updated yet')
        if overwrite:
            print('removing last month from data in order to continue overwriting data')
            predodata = predodata.isel(time=slice(None,-1))
            predadata = predadata.isel(time=slice(None,-1))
        else:
            print('exiting..')
            sys.exit()

#predodata.time.attrs = {'standard_name':'time','long_name':'Time','reference_time': pd.Timestamp('1891-01-01')}

predodata = predodata.sel(time=slice(str(styear),None))
predadata = predadata.sel(time=slice(str(styear),None))

# if predictands == ["GCEcom","20CRslp","GPCCcom"]:
#     predadata.to_netcdf('ncfiles/predadata2.nc')
#     predodata.to_netcdf('ncfiles/predodata2.nc')
#     os.system('mv ncfiles/predadata2.nc ncfiles/predadata.nc')
#     os.system('mv ncfiles/predodata2.nc ncfiles/predodata.nc')
#     sys.exit()

# *************************************************************************   
# Now start the predictor selection and the forecasting / hindcasting loop
# *************************************************************************


#sys.exit()

for p,predictand in enumerate(predictands):
    # Fill persistence predictor with predictand data
    if 'PERS' in predictorz[p]:
        if 'PERS' in predodata:  predodata = predodata.drop('PERS')
        predodata = xr.merge([predodata,predadata[predictand].rename('PERS')])
    
    print('Predictand: ',predictand)
    print('Predictors: ',predictorz[p])

    if overwrite:
        print('overwrite is True, so remove all data and redo complete forecast cycle')
        mon_range = list(range(12))
        filez = glob.glob(bdnc+'*'+predictand+'*.nc') + glob.glob(bdnc+'cor_pred/*'+predictand+'*.nc')
        for fil in filez: os.remove(fil)
    elif overwrite_m:
        mon_range = [overw_m]
        
        #filez = glob.glob(bdnc+'*'+predictand+'_'+str(overw_m).zfill(2)+'.nc')
        #for fil in filez: os.remove(fil)
    else:
        mon_range = [dt.month-1]

    print(mon_range)
    # Rolling 3-month mean, first and last timestep become nans, so remove last timestep (slice(None,-1))
    # use predictorz[p][:-1] to exclude 'PERS_TREND' from this operation as this predictor is added later
    try: predictorz[p].remove('PERS_TREND')
    except ValueError: print('PERS_TREND not in predictorz[p]') 
    
    predodata_3m = predodata[predictorz[p]].rolling(time=3,center=True).mean().isel(time=slice(None,-1))
    predadata_3m = predadata[predictand].rolling(time=3,center=True).mean().isel(time=slice(None,-1))
    
    # Change time values of predictor and predictand data for simplicity. Add 2 months for predictor data and subtract 2 months for predicand data. This means the dates do not represent the exact time off the data anymore, but is much easier for selecting the right training / testing data etc.
    #predodata_3m['time'].values = pd.DatetimeIndex(predodata_3m['time'].values) + pd.DateOffset(months=2)
    #predodata_3m['time'].values = pd.to_datetime(predodata_3m['time'].values) + pd.DateOffset(months=2)
    predodata_3m = predodata_3m.assign_coords(time=pd.to_datetime(predodata_3m['time'].values) + pd.DateOffset(months=2))
    #predadata_3m['time'].values = pd.to_datetime(predadata_3m['time'].values) - pd.DateOffset(months=2)
    predadata_3m = predadata_3m.assign_coords(time=pd.to_datetime(predadata_3m['time'].values) - pd.DateOffset(months=2))
    
    if MLR_PRED: 
        print('MLR_PRED is True, calculating trend over previous 3 months for all predictors')
        #sys.exit()
        #predodata_3m_trend = pred_trend(predodata[predictorz[p][:-1]]).isel(time=slice(None,-1))
        predodata_3m_trend = predodata[predictorz[p][:-1]].rolling(time=3,center=True).reduce(calc_trend) 
        #predodata_3m_trend['time'].values = pd.DatetimeIndex(predodata_3m_trend['time'].values) + pd.DateOffset(months=2)
        predodata_3m_trend = predodata_3m_trend.assign_coords(time=pd.to_datetime(predodata_3m_trend['time'].values) + pd.DateOffset(months=2))

    

    # Start loop over the months to update, normally this is just 1 month
    for m in mon_range:
        mon = str(m+1).zfill(2)
        
        print('prediction month = ',months[m])
        print('predictor season = ', '-'.join([months[m-3],months[m-2],months[m-1]]))
        try: print('predictor season = ', '-'.join([months[m+1],months[m+2],months[m+3]]))
        except IndexError: print('predictor season = ', '-'.join([months[m-11],months[m-10],months[m-9]]))
        
#         if HINDCAST and CAUSAL: #TODO > fix causal hindcast
#             print('Hindcasting mode, causal ',str(stvalyear),'-current')
#             timez = pd.DatetimeIndex(predodata['time'].sel(time=predodata['time.month']==m+1).values)[1:]
#             if timez[-1].month + 2 >= times[-1].month: timez = timez[:-1]
            
            
#             for y in range(np.where(timez.year == stvalyear)[0],len(timez)):
#                 train = timez[:y]
#                 test = timez[y]

#                 if predictand == 'GPCCcom':
#                     train = train[50:]
                
#                 print('test years: ',test)

#                 regr_loop(predodata_3m,predodata_3m_trend,predadata_3m,timez,train,test,ens_size,bdnc,25,predictand,predictorz[p], MLR_PRED,FC=False,sig_val = 0.1) # hier wil ik naartoe

            
        if HINDCAST and CROSVAL:
            print('Hindcasting mode, leave ',str(cv_years),' out cross-validation')
            timez = pd.DatetimeIndex(predodata_3m['time'].sel(time=predodata_3m['time.month']==m+1).values)[1:-1]

            for y in range(np.array(np.where(timez.year == stvalyear)).squeeze(),len(timez),cv_years):
                if cv_years > 1: 
                    test = timez[y+cv_years]
                else:
                    test = [timez[y]]
                train = timez.drop(test)
                
                #if predictand == 'GPCCcom': # Disregard all precipitation data before 1951
                #    train = train[50:]
                
                print('test years: ',test)
                #sys.exit()
                data_fit,beta_xr = regr_loop(predodata_3m,predodata_3m_trend,predadata_3m,timez,train,test,ens_size,bdnc,25,predictand,predictorz[p], MLR_PRED,FC=False,sig_val = 0.1) # hier wil ik naartoe
                try:
                    data_fit_tot = xr.concat([data_fit_tot,data_fit],dim='time')
                    beta_xr_tot = xr.concat([beta_xr_tot,beta_xr],dim='time')
                except NameError:
                    data_fit_tot = data_fit.copy()
                    beta_xr_tot = beta_xr.copy()
                

        elif HINDCAST:
            print('either CROSVAL or CAUSAL should be set to true')
            sys.exit()

        if FORECAST:
            print('Forecasting mode')
            timez = pd.DatetimeIndex(predodata_3m['time'].sel(time=predodata_3m['time.month']==m+1).values)
            if timez[0].year == 1901: timez = timez[1:]

            # In forecast mode, the last timestep is the test data, the rest is training data.
            train = timez[:-1]
            test = timez[-1]
            if predictand == 'GPCCcom':
                train = train[50:]

            print('test years: ',test)

            data_fit,beta_xr = regr_loop(predodata_3m,predodata_3m_trend,predadata_3m,timez,train,test,ens_size,bdnc,25,predictand,predictorz[p],MLR_PRED,FC=True,sig_val = 0.1) # hier wil ik naartoe
            
            try:
                data_fit_tot = xr.concat([data_fit_tot,data_fit],dim='time')
                beta_xr_tot = xr.concat([beta_xr_tot,beta_xr],dim='time')
            except NameError:
                data_fit_tot = data_fit.copy()
                beta_xr_tot = beta_xr.copy()
        
        #sys.exit()
        #data_fit = xr.open_dataset(bdnc+'pred_v2_'+predictand+'.nc')#,chunks={'lat':1})
        data_s5 = load_ecmwf_s5(predictand,m,data_fit_tot['obs'],bias_correct=True,resolution=resolution)
        timez_s5 = data_s5.time[:-1]

        # Add ecwmf_S5 to data_fit_tot
        data_fit_tot['ecmwf_s5'] = data_s5[predictand].rename({'number':'ens'})
                            
                
                
        data_fit_tot.to_netcdf(bdnc+'pred_v2_'+predictand+'_'+mon+'.nc')
        beta_xr_tot.to_netcdf(bdnc+'beta_v2_'+predictand+'_'+mon+'.nc')
        
    # Sort all data by time dimension
    #filn = ['pred_v2_','beta_v2_','predictors_v2_','predictors_fit_v2_']
    #for fil in filn:
    #    tmp = xr.open_dataset(bdnc+fil+predictand+'.nc')
    #    tmp.sortby('time').to_netcdf(bdnc+fil+predictand+'2.nc','w')
    #    os.remove(bdnc+fil+predictand+'.nc')
    #    os.rename(bdnc+fil+predictand+'2.nc',bdnc+fil+predictand+'.nc')
        
        #sys.exit()
    
        if VALIDATION:
            print('Calculating skill scores') 
        

            t0 = time.time()
            timez = pd.DatetimeIndex(data_fit_tot['time'].sel(time=data_fit_tot['time.month']==m+1).values)
            scores = xr.Dataset(coords={'lat': data_fit_tot['lat'],
                    'lon': data_fit_tot['lon'],
                    'time': timez[-1]}).expand_dims('time')

            # Calculate significance of ensemble mean. Calculate fraction of ensemble above or below zero
            tmp = data_fit_tot.kprep.isel(time=-1).mean('ens').values
            posneg = tmp > 0.
            above = 1.-(np.sum(data_fit_tot.kprep.isel(time=-1).values>0,axis=0)/51.)
            below = 1.-(np.sum(data_fit_tot.kprep.isel(time=-1).values<0,axis=0)/51.)
            sig_ensmean = np.ones((len(data_fit.lat),len(data_fit.lon)))
            sig_ensmean[posneg] = above[posneg]
            sig_ensmean[~posneg] = below[~posneg]

            print('month = ',str(m+1))
            # Create correlation scores and its significance
            cor,sig = linregrez(data_fit_tot.kprep.mean('ens').isel(time=slice(None,-1)).values,data_fit_tot.obs.isel(time=slice(None,-1)).values,COR=True)

            scores['cor'] = (('time','lat','lon'),cor[np.newaxis,:,:])
            scores['cor_sig'] = (('time','lat','lon'),sig[np.newaxis,:,:])
            
            scores['rmsess'] = (('time','lat','lon'),                            f_rmse(data_fit_tot['kprep'].isel(time=slice(None,-1)).values,data_fit_tot['obs'].isel(time=slice(None,-1)).values,ref=data_fit_tot['clim'].isel(time=slice(None,-1)).values,SS=True)[np.newaxis,:,:])
         
            scores['crpss'] = (('time','lat','lon'),                        f_crps2(data_fit_tot['kprep'].isel(time=slice(None,-1)).values,data_fit_tot['obs'].isel(time=slice(None,-1)).values,SS=True,ref=data_fit_tot['clim'].isel(time=slice(None,-1)).values)[np.newaxis,:,:])
            
            scores['crpss_co2'] = (('time','lat','lon'),            f_crps2(data_fit_tot['kprep'].isel(time=slice(None,-1)).values,data_fit_tot['obs'].isel(time=slice(None,-1)).values,SS=True,ref=data_fit_tot['trend'].isel(time=slice(None,-1)).values)[np.newaxis,:,:])                                   
            scores['crpss_s5'] = (('time','lat','lon'),            f_crps2(data_fit_tot['kprep'].sel(time=timez_s5).values,data_fit_tot['obs'].sel(time=timez_s5).values,SS=True,ref=data_s5[predictand].sel(time=timez_s5).values)[np.newaxis,:,:])                                     
            
            #scores['tercile'] = (('time','lat','lon'), tercile_category(data_fit_tot['kprep'].isel(time=slice(None,-1)).values,data_fit_tot['kprep'].isel(time=-1).values)[np.newaxis,:,:])
            # use 1980-2010 for tercile data
            scores['tercile'] = (('time','lat','lon'), tercile_category(data_fit_tot['kprep'].sel(time=slice('1980-01-01','2010-12-31')).values,data_fit_tot['kprep'].isel(time=-1).values)[np.newaxis,:,:])
            
            scores['for_anom'] = (('time','lat','lon'),data_fit_tot['kprep'].isel(time=-1).mean(dim='ens').values[np.newaxis,:,:])
            
            scores['for_anom_sig'] = (('time','lat','lon'),sig_ensmean[np.newaxis,:,:])
            
            scores.to_netcdf(bdnc+'scores_v2_'+predictand+'_'+mon+'.nc')
            #to_nc2(scorez,bdnc + 'scores_v2_'+predictand)
            print('Calculated skill scores for '+months[m]+', total time is '+str(np.round(time.time()-t0,2))+' seconds')
        #if os.path.isfile(bdnc+'scores_v2_'+predictand+'.nc'):
            #tmp = xr.open_dataset(bdnc+'scores_v2_'+predictand+'.nc')
            #tmp.sortby('time').to_netcdf(bdnc+'scores_v2_'+predictand+'2.nc','w')
            #os.remove(bdnc+'scores_v2_'+predictand+'.nc')
            #os.rename(bdnc+'scores_v2_'+predictand+'2.nc',bdnc+'scores_v2_'+predictand+'.nc')

        #if VALIDATION:
            #predictand = 'GCEcom' 
            print('Start validation for the last year in mon_range')
            #data_fit = xr.open_dataset(bdnc+'pred_v2_'+predictand+'.nc')
            #scores = xr.open_dataset(bdnc+'scores_v2_'+predictand+'.nc')

                
            if predictand == 'GCEcom':      
                var = 'Surface air temperature'
                clevz = np.array((-2.,-1.,-0.5,-0.2,0.2,0.5,1.,2.))
                cmap1 = matplotlib.colors.ListedColormap(['#000099','#3355ff','#66aaff','#77ffff','#ffffff','#ffff33','#ffaa00','#ff4400','#cc0022'])
                cmap2 = matplotlib.colors.ListedColormap(['#3355ff','#66aaff','#77ffff','#ffffff','#ffff33','#ffaa00','#ff4400'])
                cmap_under = '#000099'
                cmap_over = '#cc0022'
            elif predictand == 'GPCCcom':   
                var = 'Surface precipitation' 
                clevz = np.array((-200.,-100.,-50.,-20.,20.,50.,100.,200.))
                cmap1 = matplotlib.colors.ListedColormap(['#993300','#cc8800','#ffcc00','#ffee99','#ffffff','#ccff66','#33ff00','#009933','#006666'])
                cmap2 = matplotlib.colors.ListedColormap(['#cc8800','#ffcc00','#ffee99','#ffffff','#ccff66','#33ff00','#009933'])
                cmap_under = '#993300'
                cmap_over = '#006666'
                
            elif predictand == '20CRslp':
                var = 'Mean sea level pressure'
                clevz=np.array((-4.,-2.,-1.,-0.5,0.5,1.,2.,4.))
                cmap1 = matplotlib.colors.ListedColormap(['#000099','#3355ff','#66aaff','#77ffff','#ffffff','#ffff33','#ffaa00','#ff4400','#cc0022'])
                cmap2 = matplotlib.colors.ListedColormap(['#3355ff','#66aaff','#77ffff','#ffffff','#ffff33','#ffaa00','#ff4400'])
                cmap_under = '#000099'
                cmap_over = '#cc0022'

            
         
        


            #timez = pd.DatetimeIndex(data_fit['time'].sel(time=data_fit['time.month']==m+1).values)
            year = str(data_fit_tot['time.year'][-1].values)        #str(timez[-1].year)
            season = monthzz[m+1:m+4]
            print('validation for '+season+' '+year)
            
            bdpo = bdp+predictand+'/'+str(resolution)+'/'+year+mon+'/'
            if not os.path.isdir(bdpo):
                os.makedirs(bdpo)
               

            
            plot_climexp(scores.rmsess.isel(time=-1),
                            'RMSESS hindcasts, climatology as reference (1961-current)',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+' | base time: '+months[m]+' '+year,
                            predictand = predictand,
                            fname=bdpo+predictand+'_rmsess_'+year+mon+'.png',
                            clevs = np.array((-0.5,-0.35,-0.2,-0.1,0.1,0.2,0.35,0.5)),
                            cmap=cmap2,
                            cmap_under = cmap_under,
                            cmap_over = cmap_over,
                            PLOT=False,
                            )
            plot_climexp(scores.crpss.isel(time=-1),
                            'CRPSS hindcasts, reference: climatology (1961-'+str(int(year)-1)+')',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+' | base time: '+months[m]+' '+year,
                            predictand = predictand,
                            cmap=cmap2,
                            cmap_under = cmap_under,
                            cmap_over = cmap_over,
                            fname=bdpo+predictand+'_crpss_'+year+mon+'.png',
                            clevs = np.array((-0.5,-0.35,-0.2,-0.1,0.1,0.2,0.35,0.5)),
                            )    
            plot_climexp(scores.crpss_co2.isel(time=-1),
                            'CRPSS hindcasts, reference: hindcasts with only CO2 as predictor (1961-'+str(int(year)-1)+')',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+' | base time: '+months[m]+' '+year,
                            predictand = predictand,
                            cmap = cmap2,
                            cmap_under = cmap_under,
                            cmap_over = cmap_over,
                            fname=bdpo+predictand+'_crpss_detrended_clim_'+year+mon+'.png',
                            clevs = np.array((-0.5,-0.35,-0.2,-0.1,0.1,0.2,0.35,0.5)),
                            )    
            plot_climexp(scores.for_anom.isel(time=-1),
                            'Ensemble mean anomaly (wrt 1980-2010)',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+'  |  Stippled where NOT significant at 10% level'+' | base time: '+months[m]+' '+year,
                            sig=scores.for_anom_sig.isel(time=-1).values,
                            cmap=cmap2,
                            predictand = predictand,
                            cmap_under = cmap_under,
                            cmap_over = cmap_over,
                            fname=bdpo+predictand+'_ensmean_'+year+mon+'.png', 
                            clevs = clevz,
                            )
            plot_climexp(scores.cor.isel(time=-1),
                            'Correlation between hindcast anomaly and observations (1961-'+str(int(year)-1)+'',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+'  |  Stippled where signficant at 5% level'+' | base time: '+months[m]+' '+year,
                            sig = scores.cor_sig.isel(time=-1).values,
                            predictand = predictand,
                            fname=bdpo+predictand+'_correlation_'+year+mon+'.png', 
                            clevs = np.arange(-1.,1.01,0.2),
                            )
            plot_climexp(scores.tercile.isel(time=-1),
                            'Probabilty (most likely tercile of '+var+'), based on 1961-'+str(int(year)-1)+' hindcasts',
                            'SPECS Empirical Seasonal Forecast: '+var+' ('+season+' '+year+')',
                            'Ensemble size: 51 | Forecast generation date: '+dt.strftime("%d/%m/%Y")+' | base time: '+months[m]+' '+year,
                            cmap = cmap1,
                            predictand = predictand,
                            fname=bdpo+predictand+'_tercile_'+year+mon+'.png', 
                            clevs = np.array((-100,-70,-60,-50,-40,40,50,60,70,100)),
                            barticks = ['100%','70%','60%', '50%', '40%', '40%', '50%','60%', '70%', '100%'],
                            )
                            #plt.annotate('<---- below lower tercile        
            
            del(data_fit_tot,beta_xr_tot)
        
                
    import time        
    print('Total time taken is: ',np.int((time.time()-start0)//60),' minutes and ',np.int((time.time()-start0)%60), 'seconds')
    
#os.system('rsync -avt -e ssh /nobackup_1/users/krikken/KPREP/plots/ oldenbor@bvlclim.knmi.nl:climexp/SPES/plots/')
#os.system('rsync -avt /nobackup_1/users/krikken/KPREP/plots/ bhlclim:climexp/SPES/')
