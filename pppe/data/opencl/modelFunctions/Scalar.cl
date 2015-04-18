#ifndef CM_SCALAR_CL
#define CM_SCALAR_CL

/**
 * Author = Robbert Harms
 * Date = 2014-02-01
 * License = LGPL v3
 * Maintainer = Robbert Harms
 * Email = robbert.harms@maastrichtuniversity.nl
 */

/**
 * The Scalar compartment model, this just returns the input.
 */
double cmScalar(const double c){
    return c;
}

#endif // CM_SCALAR_CL