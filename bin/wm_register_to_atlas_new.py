#!/usr/bin/env python
import os
import glob
import matplotlib.pyplot as plt
import numpy
import time
import multiprocessing
import argparse

import vtk

try:
    import whitematteranalysis as wma
except:
    print "<wm_register.py> Error importing white matter analysis package\n"
    raise

#-----------------
# Parse arguments
#-----------------
parser = argparse.ArgumentParser(
    description="Registers a whole-brain vtk tractography file to another vtk tractography file (an atlas).",
    epilog="Written by Lauren O\'Donnell, odonnell@bwh.harvard.edu.  Please reference \"Unbiased Groupwise Registration of White Matter Tractography. LJ O'Donnell,  WM Wells III, Golby AJ, CF Westin. Med Image Comput Comput Assist Interv. 2012;15(Pt 3):123-30.\"",
    version='1.0')


parser.add_argument(
    'inputSubject',
    help='One subject data: whole-brain tractography as vtkPolyData (.vtk or .vtp).')
parser.add_argument(
    'inputAtlas',
    help='An atlas, one file containing whole-brain tractography as vtkPolyData (.vtk or .vtp).')
parser.add_argument(
    'outputDirectory',
    help='The output directory will be created if it does not exist.')
parser.add_argument(
    '-mode', action="store", dest="mode", type=str, default="affine",
    help='The mode can be affine or nonlinear. Affine is the default. It should be run first before nonlinear.')
parser.add_argument(
    '-f', action="store", dest="numberOfFibers", type=int, default=20000,
    help='Total number of fibers to analyze from each dataset. During registration, at each iteration fibers are randomly sampled from within this data. 20000 is the default number of total fibers.')
parser.add_argument(
    '-l', action="store", dest="fiberLength", type=int, default=80,
    help='Minimum length (in mm) of fibers to analyze. 60mm is reasonable for DTI single-tensor tractography which is shorter in general. Use a higher value such as 80 or 100 for two-tensor or other advanced tractography. This parameter removes short, noisy fibers and focuses on larger structures that can be registered well. For neonate data, a value of 40mm is suggested. The default is 80mm.')
parser.add_argument(
    '-lmax', action="store", dest="fiberLengthMax", type=int, default=150,
    help='Maximum length (in mm) of fibers to analyze. This parameter can be used to remove extremely long fibers that may have traversed several structures. For example, a value of 150 will avoid sampling the tail end of the fiber length distribution. The default is 150 mm.')
parser.add_argument(
    '-verbose', action='store_true', dest="flag_verbose",
    help='Verbose. Run with -verbose to store more files and images of intermediate and final polydatas.')
#parser.add_argument(
#    '-pf', action="store", dest="pointsPerFiber", type=int, default=15,
#    help='Number of points for fiber representation during registration. The default of 15 is reasonable.')
 
args = parser.parse_args()

print "\n\n<register> =========GROUP REGISTRATION============"
print "<register> Registering to atlas."
print "<register> Input  subject file: ", args.inputSubject
print "<register> Input  atlas file: ", args.inputAtlas
print "<register> Output directory: ", args.outputDirectory
print "\n<register> ============PARAMETERS================="

mode = args.mode
print "<register> Registration mode:", mode

if not os.path.isfile(args.inputSubject):
    print "<register> Error: Input subject data", args.inputSubject, "does not exist."
    exit()

if not os.path.isfile(args.inputAtlas):
    print "<register> Error: Input atlas", args.inputAtlas, "does not exist."
    exit()

fname = args.inputSubject
subject_id = os.path.splitext(os.path.basename(fname))[0]
subject_pd = wma.io.read_polydata(fname)
fname = args.inputAtlas
atlas_id = os.path.splitext(os.path.basename(fname))[0]
atlas_pd = wma.io.read_polydata(fname)

outdir = args.outputDirectory
if not os.path.exists(outdir):
    print "<register> Output directory", outdir, "does not exist, creating it."
    os.makedirs(outdir)
subject_outdir = os.path.join(outdir, subject_id)


number_of_fibers = args.numberOfFibers
print "<register> Number of fibers to analyze per subject: ", number_of_fibers

fiber_length = args.fiberLength
print "<register> Minimum length of fibers to analyze (in mm): ", fiber_length

fiber_length_max = args.fiberLengthMax
print "<register> Maximum  length of fibers to analyze (in mm): ", fiber_length_max

if args.flag_verbose:
    print "<register> Verbose display and intermediate image saving ON."
else:
    print "<register> Verbose display and intermediate image saving OFF."
verbose = args.flag_verbose

print "\n<register> Starting registration...\n"


        
register = wma.congeal_to_atlas.SubjectToAtlasRegistration()
register.output_directory = subject_outdir
register.input_polydata_filename = args.inputSubject

# -------------
# SETTINGS
# -------------

points_per_fiber = 10

if mode == "affine":
    # default affine for adults with fewer fibers than neonate brains (lower variability)
    sigma_per_scale = [30, 10, 7.5, 5]
    # We don't need so many iterations because the atlas mean brain is already done, but these are really fast.
    iterations_per_scale=[2, 2, 2, 2]
    maxfun_per_scale = [45, 60, 75, 90]
    mean_brain_size_per_scale = [1000, 3000, 4000, 5000]
    subject_brain_size_per_scale = [250, 1500, 1750, 2000]
    initial_step_per_scale = [10, 5, 5, 5]
    final_step_per_scale = [5, 2, 2, 2]
    register.nonlinear = False
    
elif mode == "affine_neonate":
    # Try smaller sigma for neonates
    sigma_per_scale = [20, 10, 7.5, 5]
    # We don't need so many iterations because the atlas mean brain is already done, but these are really fast.
    iterations_per_scale=[2, 2, 2, 2]
    maxfun_per_scale = [50, 80, 80, 200]
    mean_brain_size_per_scale = [1000, 3000, 5000, 7500]
    subject_brain_size_per_scale = [250, 1500, 2000, 2500]
    initial_step_per_scale = [10, 5, 5, 5]
    final_step_per_scale = [5, 2, 2, 2]
    register.nonlinear = False

elif mode == "nonlinear":
    # this is in mm space.
    initial_step_per_scale = [5, 3, 2]
    final_step_per_scale = [2, 1, 1]
    # use only very local information (small sigma)
    sigma_per_scale = [3, 2, 1]
    # how many times to repeat the process at each scale
    iterations_per_scale = [1, 1, 1]
    # the mean brain is set already so we just want to sample a good amount here
    mean_brain_size_per_scale = [2000, 2000, 2000]
    subject_brain_size_per_scale = [500, 750, 900]
    # stop computation early. no need to converge at first iteration, just improve objective as quickly as possible
    # These settings are for a 5x5x5 grid, 125*3 = 375 parameter space.
    maxfun_per_scale = [375, 500, 750]
    # fiber representation for computation.
    points_per_fiber = 15
    register.nonlinear = True

elif mode == "affineTEST":
    # very quick test if software is working
    sigma_per_scale = [30, 10, 7.5]
    iterations_per_scale=[1, 1, 1]
    maxfun_per_scale = [60, 80, 100]
    mean_brain_size_per_scale = [1500, 2000, 3000]
    subject_brain_size_per_scale = [100, 500, 1000]
    initial_step_per_scale = [5, 5, 5, 5]
    final_step_per_scale = [2, 2, 2, 2]
    register.nonlinear = False
    
elif mode == "nonlinearTEST":
    # very quick test if software is working
    initial_step_per_scale = [5, 3, 1]
    final_step_per_scale = [2, 1, 0.05]
    sigma_per_scale = [3, 2, 1]
    iterations_per_scale = [1, 1, 1]
    mean_brain_size_per_scale = [1500, 2000, 3000]
    subject_brain_size_per_scale = [500, 750, 1000]
    # stop computation: this is just a quick test the software is working
    maxfun_per_scale = [10, 10, 10]
    points_per_fiber = 15
    register.nonlinear = True

else:
    print "\n<register> Error: Unknown registration mode:", mode
    exit()


    
# We have to add polydatas after setting nonlinear in the register object
register.set_subject(subject_pd, subject_id)
register.set_atlas(atlas_pd, atlas_id)


register.points_per_fiber = points_per_fiber

# -------------
# Done SETTINGS. Below is computation
# -------------
total_iterations = numpy.sum(numpy.array(iterations_per_scale))
iteration = 1
# estimate percentage complete based on number of fibers compared,
# because the times cobyla calls the objective function are approx
# constant per scale (except first scale where they are cut short)
total_comparisons = numpy.multiply(iterations_per_scale,numpy.multiply(numpy.array(mean_brain_size_per_scale), numpy.array(subject_brain_size_per_scale)))
total_comparisons = numpy.sum(total_comparisons)
comparisons_so_far = 0

do_scales = range(len(sigma_per_scale))

for scale in do_scales:
    register.sigma = sigma_per_scale[scale]
    register.initial_step = initial_step_per_scale[scale]
    register.final_step = final_step_per_scale[scale]
    register.maxfun = maxfun_per_scale[scale]
    register.mean_brain_size = mean_brain_size_per_scale[scale]
    register.subject_brain_size = subject_brain_size_per_scale[scale]
    
    for idx in range(0,iterations_per_scale[scale]):
        register.iterate()
        comparisons_this_scale = mean_brain_size_per_scale[scale]*subject_brain_size_per_scale[scale]
        comparisons_so_far += comparisons_this_scale
        percent = 100*(float(comparisons_so_far)/total_comparisons)
        print "Done iteration", iteration, "/", total_iterations, ". Percent finished approx:", "%.2f" % percent
        iteration += 1
        # Intermediate save. For testing only.
        if verbose:
            register.save_transformed_polydata(intermediate_save=True)

# Final save when we are done
register.save_transformed_polydata()

print "Done registering."
