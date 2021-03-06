"""
Created on Thu Jun 22 10:45:04 2017

@author: rjackson
"""

from netCDF4 import Dataset
from datetime import datetime, timedelta
from glob import glob
import numpy as np
import pandas
import sys
import time
import xarray

from dask import delayed, compute
from distributed import Client, LocalCluster


def get_conv_strat(date, shape):
    year_str = "%04d" % date.year
    month_str = "%02d" % date.month

    day_str = "%02d" % date.day
    hour_str = "%02d" % date.hour
    minute_str = "%02d" % date.minute
    conv_strat_path = ('/lcrc/group/earthscience/rjackson/conv_stratiform/' +
                       year_str + '/' + month_str + '/' + day_str +
                       '/cpol_conv_strat' + year_str + month_str + day_str +
                       hour_str + minute_str + '.nc')
    try:
        data_cdf = Dataset(conv_strat_path)
        conv_strat = data_cdf.variables['strat_conv'][:]
    except:
        conv_strat = np.zeros(shape)
        print(('Cound not find convective-stratiform classification for ' +
               year_str + '-' + month_str + '-' + day_str + ' ' + hour_str +
               ':' + minute_str))
    return conv_strat

# Generate histogram for each file in list
def get_histogram_from_file(file):
    nested_Dataset = xarray.open_mfdataset(file)
    cpol_T = nested_Dataset.variables['cpol_T'][:]
    times = nested_Dataset.variables['time'][:].data
    hour_bins = np.arange(0, 24, 1)
    hist_break = np.zeros((len(height_bins)-1, 8, len(year_bins)))
    hist_monsoon = np.zeros((len(height_bins)-1, 8, len(year_bins)))
    hist_total = np.zeros((len(height_bins)-1, 8, len(year_bins)))
    the_shape = cpol_T.data.shape
    ts = []
    dates = []
    years = []
    months = []
    days = []
    for timestamps in times:
        the_datetime = datetime.utcfromtimestamp(timestamps.tolist()/1e9)
        ts.append(the_datetime)
        years.append(the_datetime.year)
        months.append(the_datetime.month)
        days.append(the_datetime.day)
    years = np.array(years)
    months = np.array(months)
    days = np.array(days)
    ts = np.array(ts)

    # Get timestamp of first and last day
    first = ts[0]
    last = ts[-1]
    cur = first

    while(cur <= last):
        tyear = cur.year
        tmonth = cur.month
        tday = cur.day
        hist_inds = np.where(np.logical_and(np.logical_and(years == tyear,
                                                           months == tmonth),
                                            days == tday))
        the_ind = np.where(np.logical_and(np.logical_and(year == tyear,
                                                         month == tmonth),
                                          day == tday))
        mjo_ind = np.where(np.logical_and(np.logical_and(yearm == tyear,
                                                         monthm == tmonth),
                                          daym == tday))
        if(len(hist_inds[0]) > 0):
            conv_strat = np.stack([get_conv_strat(t, (the_shape[1], the_shape[2]))
                                   for t in ts[hist_inds[0]]])
            the_data = np.array(cpol_T[hist_inds].data)
            indicies_not = np.where(np.logical_not(conv_strat == conv_index))
            print(len(indicies_not[0])/np.size(conv_strat))
            the_data[indicies_not] = np.nan
            z, x, y = np.meshgrid(np.zeros(the_data.shape[0]), range(0,201), range(0,201), indexing='ij')
            dist = np.sqrt(np.square(x-100) + np.square(y-100))
            #indicies_not_center = np.where(dist < 35)
            the_data[np.where(dist < 25.0)] = np.nan
            the_data[the_data > 20500] = np.nan
            print(str(100 - len(np.where(the_data > 0)[0])/np.size(the_data)*100) + '% of points used')
            for hour in hour_bins:
                hour_inds = np.where(ts[hist_inds[0]] == hour)
                hour_ind = int(hour)
                teh_data = the_data[hour_inds
                hist, bins = np.histogram(the_data[np.isfinite(the_data)], bins=height_bins) 
                if(groups[the_ind[0]] == 0):
                    hist_break[:, mjo_index-1, hour_ind] += hist
                elif(groups[the_ind[0]] == 1):
                    hist_monsoon[:, mjo_index-1, hour_ind] += hist
                hist_total[:, mjo_index-1, hour_ind] += hist
            
            mjo_index = int(index[mjo_ind])
            hour_ind = tyear-hour_bins[0]
            print(the_data[the_data > 0])
            

        cur += timedelta(days=1)
    the_shape = hist_break.shape
    return_array = np.zeros((the_shape[0], the_shape[1], len(hour_bins), 3))
    return_array[:, :, :, 0] = hist_break
    return_array[:, :, :, 1] = hist_monsoon
    return_array[:, :, :, 2] = hist_total
    return return_array


if __name__ == '__main__':
    print('Starting processing...')

    file_list = '/lcrc/group/earthscience/rjackson/echo_tops/echo_tops*'
    file_path = '/home/rjackson/data/Drosdowsky.cdf'
    mjo_index_file = '/home/rjackson/data/rmm.74toRealtime.txt'
    in_netcdf = Dataset(file_path)
    year = in_netcdf.variables['year'][:]
    month = in_netcdf.variables['month'][:]
    day = in_netcdf.variables['day'][:]
    groups = in_netcdf.variables['groups'][:]
    in_netcdf.close()
    file_list = glob(file_list)
    conv_index = int(sys.argv[1])
    
    # Read MJO index
    data = pandas.read_csv(mjo_index_file,
                           header=2,
                           delim_whitespace=True)
    data_matrix = np.ma.array(data.values)
    yearm = data_matrix[:, 0]
    monthm = data_matrix[:, 1]
    daym = data_matrix[:, 2]
    index = data_matrix[:, 5]
    height_bins = np.arange(0, 20000, 500)
    year_bins = np.arange(1998, 2018, 1)
    # Start a cluster with x workers
    cluster = LocalCluster(n_workers=16)
    client = Client(cluster)

    #x = get_histogram_from_file(file_list[54])
    #print(x[:,:,:,2])
    get_histogram = delayed(get_histogram_from_file)
    histograms = [get_histogram(files)
                  for files in file_list]
    histograms = compute(*histograms)
    histograms = np.stack(histograms)
    histograms = np.sum(histograms, axis=0)
    hist_breaks = histograms[:, :, :, 0]
    hist_monsoons = histograms[:, :, :, 1]
    hist_totals = histograms[:, :, :, 2]

    out_netcdf = Dataset(('echo_top_histograms' + sys.argv[1] + '.cdf'),
                          mode='w')
    out_netcdf.createDimension('bins', len(height_bins))
    out_netcdf.createDimension('bin_levels', len(height_bins)-1)
    out_netcdf.createDimension('mjo_index', 8)
    out_netcdf.createDimension('year_bins', len(year_bins))
    year = out_netcdf.createVariable('years', year_bins.dtype,('year_bins'))
    year[:] = year_bins

    hist_break = out_netcdf.createVariable('hist_break', hist_breaks.dtype,
                                           (('bin_levels', 'mjo_index', 'year_bins')))
    hist_break.long_name = 'Frequency histogram of echo top heights in break'
    hist_break.units = '#'
    hist_break[:] = hist_breaks

    hist_monsoon = out_netcdf.createVariable('hist_monsoon', hist_monsoons.dtype,
                                            (('bin_levels', 'mjo_index','year_bins')))
    hist_monsoon.long_name = 'Frequency histogram of echo top heights in break'
    hist_monsoon.units = '#'
    hist_monsoon[:] = hist_monsoons
    
    hist_total = out_netcdf.createVariable('hist_total', hist_totals.dtype,
                                          (('bin_levels', 'mjo_index','year_bins')))
    hist_total.long_name = 'Frequency histograms of echo top heights'
    hist_total.units = '#'
    hist_total[:] = hist_totals

                                          
    out_netcdf.close()
    Client.shutdown(timeout=10)
