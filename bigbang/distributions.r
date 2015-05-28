library(poweRlaw) #Power law package influenced by Cosma Shalizi 
library(fitdistrplus) #Will use package later

##############################################################################################
#Plotting Sample Data
##############################################################################################

#Create random data to work with 
lognorm_samp = rlnorm(100, 0, 1)  #100 samples of log normal distribution with mean = 0, var = 1
powerlaw_samp = rplcon(100, 1, 3) #100 samples w/ xmin = 1, alpha = 3

#Plots of data w/ actual density overlayed on top 
mean = 0; var = 1 
xmin = 1; alpha = 3
x = seq(xmin, 10, length.out=1000)
hist(powerlaw_samp, prob = T)
lines(x, dplcon(x, xmin, alpha), type="l")
plot(x, pplcon(x, xmin, alpha), type="l", main="CDF Power Law", ylab = "probability swept")

hist(lognorm_samp, prob = T)
lines(x, dlnorm(x, mean, var), type="l")
plot(x, plnorm(x, mean, var), type="l", main="CDF LogNormal", ylab = "probability swept")

#QQ plot of sample powerlaw data
qqnorm(log(powerlaw_samp), main = "PowerLaw Sample")

#QQ plot of sample lognormal data
qqnorm(log(lognorm_samp), main = "LogNormal Sample")

##############################################################################################
#Comparing Log-Normal and Power-Law Distributions 
##############################################################################################

########## Helper Functions ##########

#Returns an array (of size num_samples) of lists where the ith list is a sample drawn from a  
#lognormal dist w/ size = size_vec[i], mean = mean_vec[i], var = var_vec[i]. 
LogNormalSampleGen <- function(num_samples, size_vec, mean_vec, var_vec) {
	all_samples = array(list(), num_samples)
	for (i in 1:num_samples) {
		all_samples[[i]] = rlnorm(size_vec[i], mean_vec[i], var_vec[i])
	}
	return(all_samples)
}

#Returns an array of lists where the ith list is a sample drawn from a powerlaw dist w/ 
#size = size_vec[i], xmin = xmin_vec[i], alpha = alpha_vec[i]
PowerLawSampleGen <- function(num_samples, size_vec, xmin_vec, alpha_vec) {
	all_samples = array(list(), num_samples)
	for (i in 1:num_samples) {
		all_samples[[i]] = rplcon(size_vec[i], xmin_vec[i], alpha_vec[i])
	}
	return(all_samples)
}

#arr is the array returned by calling LogNormalSampleGen. This function creates an array of distribution 
#objects (the distribution object contains information such as KS statistic) 
LogNormalObjectGen <- function(arr) {
	all_distr = array(list(), length(arr))
	for (i in 1:length(arr)) {
		data = arr[[i]]
		power_obj = conlnorm$new(data) #conlnorm is continuous log-normal
		all_distr[[i]] = power_obj #Check if sampling from discrete log-normal matters (do this later)
	}
	return(all_distr)
}

#arr is the array returned by calling PowerLawSampleGen. This function creates an array of distribution 
#objects. 
PowerLawObjectGen <- function(arr) {
	all_distr = array(list(), length(arr))
	for (i in 1:length(arr)) {
		data = arr[[i]]
		power_obj = conpl$new(data) #conpl is continuous power-law
		all_distr[[i]] = power_obj #Check if sampling from discrete powerlaw matters (do this later)
	}
	return(all_distr)
}

#FIX
LogNormalEstParams <- function(arr_distr) {
	all_params = array(list(), length(arr_distr))
	for (i in 1:length(arr_distr)) {
		dist_obj = arr_distr[[i]]
		est = estimate_pars(dist_obj)
		all_params[[i]] = est
	}
	return(all_params)
}

#FIX
PowerLawEstParams <- function(arr_distr) {
	all_params = array(list(), length(arr_distr))
	for (i in 1:length(arr_distr)) {
		dist_obj = arr_distr[[i]]
		est = estimate_pars(dist_obj)
		all_params[[i]] = est
	}
	return(all_params)
}
#####################################

#Generate samples
num_samples = 240 #Choose so that divisible by 2, 3, and 4
size_vec =  rep(c(100, 500), num_samples / 2)
mean_vec =  rep(c(1, 10, 50, 100), num_samples / 4)
var_vec = rep(c(1, 9, 36, 81), num_samples / 4)
lognorm_samples = LogNormalSampleGen(num_samples, size_vec, mean_vec, var_vec)

xmin_vec = rep(c(1, 5, 10, 100), num_samples / 4)
alpha_vec = rep(c(1.5, 2, 3, 4), num_samples / 4)
powerlaw_samples = PowerLawSampleGen(num_samples, size_vec, xmin_vec, alpha_vec)

##########Estimate Parameters##########

#The first 80 samples will be fitted using MLE, next 80 by moments estimation, and the
#last remaining 80 using bootstrap methods (each of the 80 samples have identical mean/var/xmin vectors) 

lognorm_mle_samp = lognorm_samples[1:80]
powerlaw_mle_samp = powerlaw_samples[1:80]
lognorm_mle_obj = LogNormalObjectGen(lognorm_mle_samp)
powerlaw_mle_obj = PowerLawObjectGen(powerlaw_mle_samp)

lognorm_moments_samp = lognorm_samples[81:160] #TDL
powerlaw_moments_samp  = powerlaw_samples[81:160] #TDL

lognorm_boot_samp = lognorm_samples[161:240] #TDL
powerlaw_boot_samp  = powerlaw_samples[161:240] #TDL

#MLE estimate (xmin is calculated using goodness-of-fit based approach)
params_mle_lognorm = LogNormalEstParams(lognorm_mle_obj)
params_mle_powerlaw = PowerLawEstParams(powerlaw_mle_obj)

#Method of Moments estimate
#NEED TO CREATE/FIND FUNTIONS TO DO THIS - I THINK FITDSTRPLUS DOES THIS

#Bootrap estimate 
#NEED TO CREATE/FIND FUNTIONS TO DO THIS - I THINK FITDSTRPLUS and POWERRLAW DOES THIS

########## Checking if Fitted Distribution Comes from Right Family ##########

#Use AIC test, log liklihood test, goodness-of-fit test

########## Visualization of Results ##########

