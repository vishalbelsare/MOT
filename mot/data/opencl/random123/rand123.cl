#ifndef _RAND123_DOT_CL
#define _RAND123_DOT_CL

/**
 * This CL file is the MOT interface to the rand123 library. It contains various random number generating functions
 * for generating random numbers in uniform and gaussian distributions.
 *
 * The rand123 supports various modes and precisions, in this front-end we have chosen for a precision of 4 words
 * of 32 bits (In rand123 terms, we have the 4x32 bit generators).
 */

/**
 * The information needed by the random functions to generate unique random numbers.
 * The elements of this struct are unsigned integers with N words of W bits (specified by the
 * generator function in use).
 */
typedef struct{
    %(GENERATOR_NAME)s4x32_ctr_t counter;
    %(GENERATOR_NAME)s4x32_key_t key;
} rand123_data;

/**
 * Generates the random bits used by the random functions
 */
uint4 rand123_generate_bits(rand123_data* rng_data){

    %(GENERATOR_NAME)s4x32_ctr_t* ctr = &rng_data->counter;
    %(GENERATOR_NAME)s4x32_key_t* key = &rng_data->key;

    union {
        %(GENERATOR_NAME)s4x32_ctr_t ctr_el;
        uint4 vec_el;
    } u;

    u.ctr_el = %(GENERATOR_NAME)s4x32(*ctr, *key);
    return u.vec_el;
}

/**
 * Initializes the rand123_data structure.
 *
 * The provided key is extended with the global id of the kernel and a zero for possible future use.
 */
rand123_data rand123_initialize_data(uint counter[4], uint key[2]){
    %(GENERATOR_NAME)s4x32_ctr_t c = {{counter[0], counter[1], counter[2], counter[3]}};
    %(GENERATOR_NAME)s4x32_key_t k = {{key[0], key[1], get_global_id(0), 0}};

    rand123_data rng_data = {c, k};
    return rng_data;
}

/**
 * Initializes the rand123_data structure with additional precision (extra key) using constant memory pointers.
 *
 * The same function as ``rand123_initialize_data`` but this accepts ``constant`` memory pointers.
 */
rand123_data rand123_initialize_data_constmem(constant uint counter[4], constant uint key[2]){
    return rand123_initialize_data(
        (uint []){counter[0], counter[1], counter[2], counter[3]},
        (uint []){key[0], key[1]});
}

/**
 * Increments the rand123 state counters for the next iteration.
 *
 * One needs to call this function after every call to a random number generating function
 * to ensure the next number will be different.
 */
void rand123_increment_counters(rand123_data* rng_data){
    if (++rng_data->counter.v[0] == 0){
        if (++rng_data->counter.v[1] == 0){
            ++rng_data->counter.v[2];
        }
    }
}

/**
 * Applies the Box-Muller transformation on four uniformly distributed random numbers.
 *
 * This transforms uniform random numbers into Normal distributed random numbers.
 */
double4 rand123_box_muller_double4(double4 x){
    double r0 = sqrt(-2 * log(x.x));
    double c0;
    double s0 = sincos(((double) 2 * M_PI) * x.y, &c0);

    double r1 = sqrt(-2 * log(x.z));
    double c1;
    double s1 = sincos(((double) 2 * M_PI) * x.w, &c1);

    return (double4) (r0*c0, r0*s0, r1*c1, r1*s1);
}

float4 rand123_box_muller_float4(float4 x){
    float r0 = sqrt(-2 * log(x.x));
    float c0;
    float s0 = sincos(((double) 2 * M_PI) * x.y, &c0);

    float r1 = sqrt(-2 * log(x.z));
    float c1;
    float s1 = sincos(((double) 2 * M_PI) * x.w, &c1);

    return (float4) (r0*c0, r0*s0, r1*c1, r1*s1);
}
/** end of Box Muller transforms */

/** Random number generating functions in the Rand123 space */
double4 rand123_uniform_double4(rand123_data* rng_data){
    uint4 generated_bits = rand123_generate_bits(rng_data);
    return ((double) (1/pown(2.0, 32))) * convert_double4(generated_bits) +
        ((double) (1/pown(2.0, 64))) * convert_double4(generated_bits);
}

double4 rand123_normal_double4(rand123_data* rng_data){
    return rand123_box_muller_double4(rand123_uniform_double4(rng_data));
}

float4 rand123_uniform_float4(rand123_data* rng_data){
    uint4 generated_bits = rand123_generate_bits(rng_data);
    return (float)(1/pown(2.0, 32)) * convert_float4(generated_bits);
}

float4 rand123_normal_float4(rand123_data* rng_data){
    return rand123_box_muller_float4(rand123_uniform_float4(rng_data));
}
/** End of the random number generating functions */


/** Implementations of the random.h header */
double4 rand4(void* rng_data){
    double4 val = rand123_uniform_double4((rand123_data*)rng_data);
    rand123_increment_counters((rand123_data*)rng_data);
    return val;
}

double4 randn4(void* rng_data){
    double4 val = rand123_normal_double4((rand123_data*)rng_data);
    rand123_increment_counters((rand123_data*)rng_data);
    return val;
}

float4 frand4(void* rng_data){
    float4 val = rand123_uniform_float4((rand123_data*)rng_data);
    rand123_increment_counters((rand123_data*)rng_data);
    return val;
}

float4 frandn4(void* rng_data){
    float4 val = rand123_normal_float4((rand123_data*)rng_data);
    rand123_increment_counters((rand123_data*)rng_data);
    return val;
}

double rand(void* rng_data){
    return rand4(rng_data).x;
}

double randn(void* rng_data){
    return randn4(rng_data).x;
}

float frand(void* rng_data){
    return frand4(rng_data).x;
}

float frandn(void* rng_data){
    return frandn4(rng_data).x;
}

#endif // _RAND123_DOT_CL
