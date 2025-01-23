#!/bin/sh

# Script to run empirical seasonal prediction system for TAS, PREC and PSL.
# User to specify predictand variable names
# F. Krikken, KNMI, 2017.12.07
# ---------------------------
res=$1

# Copy grid description file to correct place
#cp griddes${res}.txt ~/climexp_data/KPREPData/targetgrid/
# Change working directory to where to store data / files / plots / etc.

# First get resolution..

# First get TMAX at 1 degree resolution for the MDC forecast

#wget -N https://climexp.knmi.nl/ERA5/era5_tmax.nc -P inputdata/
#cdo remapbil,targetgrid/griddes10.txt inputdata/era5_tmax.nc inputdata/era5_tmax_r10.nc

wget -N http://climexp.knmi.nl/BerkeleyData/land_mask.nc -P inputdata/
wget -N http://climexp.knmi.nl/BerkeleyData/TMAX_LatLong1.nc -P inputdata/
cdo remapbil,global_$res inputdata/land_mask_TMAX_LatLong1.nc inputdata/land_mask_TMAX_LatLong1_r10.nc
cdo remapbil,global_$res inputdata/TMAX_LatLong1.nc inputdata/TMAX_LatLong1_r10.nc




# Now for the other forecast

## NEAR SURFACE TEMPERATURE / SEA SURFACE TEMPERATURE

# Download ERSSTV5 from climexp
wget -N http://climexp.knmi.nl/NCDCData/ersstv5.nc -P inputdata/
# Download GHCN_CAMS from NCEP
# Upgrade to 1 degree, download 0.5 degrees
wget -N ftp://ftp.cdc.noaa.gov/Datasets/ghcncams/air.mon.mean.nc -P inputdata/

cdo -L settunits,days -fillmiss -mergegrid -addc,273.15 -selyear,1948/2030 -remapbil,global_${res} -setmissval,-999 inputdata/ersstv5.nc -remapbil,global_${res} -setmissval,-999 inputdata/air.mon.mean.nc inputdata/gcecom_r${res}.nc



# Download Hadley4 with kriging
wget -N http://www-users.york.ac.uk/~kdc3/papers/coverage2013/had4_krig_v2_0_0.nc.gz -P inputdata/
gunzip -f inputdata/had4_krig_v2_0_0.nc.gz
cdo -remapbil,global_${res} -selyear,1901/2010 inputdata/had4_krig_v2_0_0.nc inputdata/had4_krig_v2_0_0_r${res}.nc


## SEA LEVEL PRESSURE
# Download SLP data from climate explorer
wget -N http://climexp.knmi.nl/20CRv3/prmsl.mon.mean.nc -P inputdata/          # Data from 1851 to 2011
wget -N http://climexp.knmi.nl/NCEPNCAR40/slp.mon.mean.nc -P inputdata/     # Data from 1948 to current

# Use prmsl.mon.mean.nc for 1901 to 1948 and slp.mon.mean.nc for 1948 to current
rm -f inputdata/slp_mon_mean_1901-current_r${res}.nc
cdo -L mergetime -selyear,1901/1947 -remapbil,global_${res} -selvar,prmsl -divc,100 inputdata/prmsl.mon.mean.nc -remapbil,global_${res} inputdata/slp.mon.mean.nc inputdata/slp_mon_mean_1901-current_r${res}.nc

## PRECIPITATION DATA
# Download GPCC precipitation data from climexp
wget -N http://climexp.knmi.nl/GPCCData/gpcc_10_combined.nc -P inputdata/
# Multiply by days per month to get monthly data
cdo muldpm inputdata/gpcc_10_combined.nc inputdata/gpcc_10_combined_mon.nc
# Regrid data to specified resolution
cdo remapbil,global_$res inputdata/gpcc_10_combined_mon.nc inputdata/gpcc_10_combined_mon_r${res}.nc

	

## CLIMATE INDICES
# Download the climate indices from climate explorer
wget -N http://climexp.knmi.nl/CDIACData/RCP45_CO2EQ_mo.dat -P inputdata/
wget -N http://climexp.knmi.nl/NCDCData/ersst_nino3.4a.dat -P inputdata/
#wget -N http://climexp.knmi.nl/NCDCData/qbo_30.dat -P inputdata/
wget -N http://climexp.knmi.nl/NCDCData/dmi_ersst.dat -P inputdata/
wget -N http://climexp.knmi.nl/UWData/pdo_ersst.dat -P inputdata/
wget -N http://climexp.knmi.nl/NCDCData/amo_ersst_ts.dat -P inputdata/

## TESTING
## MJO
wget -N http://passage.phys.ocean.dal.ca/~olivere/data/mjoindex_IHR_20CRV3.dat -P inputdata/
wget -N https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_mjo_index/proj_norm_order.ascii -P inputdata/
## Warm water volume
wget -N http://climexp.knmi.nl/BMRCData/wwv_poama.dat -P inputdata
## NINO12
wget -N http://climexp.knmi.nl/NCDCData/ersst_nino12a.dat -P inputdata



