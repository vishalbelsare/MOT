import logging
import pyopencl as cl
import numpy as np
from ...utils import get_float_type_def
from ...cl_routines.base import AbstractCLRoutine
from ...load_balance_strategies import Worker


__author__ = 'Robbert Harms'
__date__ = "2014-05-18"
__license__ = "LGPL v3"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class CodecRunner(AbstractCLRoutine):

    def __init__(self, cl_environments, load_balancer, double_precision=False):
        """This class can run the codecs used to transform the parameters to and from optimization space.

        Args:
            double_precision (boolean): if we will use the double (True) or single floating (False) type for the calculations
        """
        super(CodecRunner, self).__init__(cl_environments, load_balancer)
        self._logger = logging.getLogger(__name__)
        self._double_precision = double_precision

    def decode(self, codec, data):
        """Decode the parameters.

        This transforms the data from optimization space to model space.

        Args:
            codec (AbstractCodec): The codec to use in the transformation.
            data (ndarray): The parameters to transform to model space

        Returns:
            ndarray: The array with the transformed parameters.
        """
        if len(data.shape) > 1:
            from_width = data.shape[1]
        else:
            from_width = 1

        if from_width != codec.get_nmr_parameters():
            raise ValueError("The width of the given data does not match the codec expected width.")

        return self._transform_parameters(codec.get_cl_decode_function('decodeParameters'), 'decodeParameters', data,
                                          codec.get_nmr_parameters())

    def encode(self, codec, data):
        """Encode the parameters.

        This transforms the data from model space to optimization space.

        Args:
            codec (AbstractCodec): The codec to use in the transformation.
            data (ndarray): The parameters to transform to optimization space

        Returns:
            ndarray: The array with the transformed parameters.
        """
        if len(data.shape) > 1:
            from_width = data.shape[1]
        else:
            from_width = 1

        if from_width != codec.get_nmr_parameters():
            raise ValueError("The width of the given data does not match the codec expected width.")

        return self._transform_parameters(codec.get_cl_encode_function('encodeParameters'), 'encodeParameters', data,
                                          codec.get_nmr_parameters())

    def _transform_parameters(self, cl_func, cl_func_name, data, nmr_params):
        np_dtype = np.float32
        if self._double_precision:
            np_dtype = np.float64
        data = data.astype(np_dtype, order='C', copy=False)
        rows = data.shape[0]
        workers = self._create_workers(_CodecWorker, [cl_func, cl_func_name, data, nmr_params, self._double_precision])
        self.load_balancer.process(workers, rows)
        return data


class _CodecWorker(Worker):

    def __init__(self, cl_environment, cl_func, cl_func_name, data, nmr_params, double_precision):
        super(_CodecWorker, self).__init__(cl_environment)
        self._cl_func = cl_func
        self._cl_func_name = cl_func_name
        self._data = data
        self._nmr_params = nmr_params
        self._double_precision = double_precision
        self._kernel = self._build_kernel()

    def calculate(self, range_start, range_end):
        nmr_problems = range_end - range_start
        read_write_flags = self._cl_environment.get_read_write_cl_mem_flags()

        param_buf = cl.Buffer(self._cl_run_context.context, read_write_flags,
                              hostbuf=self._data[range_start:range_end, :])

        self._kernel.transformParameterSpace(self._cl_run_context.queue, (int(nmr_problems), ), None, param_buf)
        event = cl.enqueue_copy(self._cl_run_context.queue, self._data[range_start:range_end, :], param_buf, is_blocking=False)
        return event

    def _get_kernel_source(self):
        kernel_source = ''
        kernel_source += get_float_type_def(self._double_precision)
        kernel_source += self._cl_func
        kernel_source += '''
            __kernel void transformParameterSpace(global MOT_FLOAT_TYPE* x_global){
                int gid = get_global_id(0);

                MOT_FLOAT_TYPE x[''' + str(self._nmr_params) + '''];

                for(int i = 0; i < ''' + str(self._nmr_params) + '''; i++){
                    x[i] = x_global[gid * ''' + str(self._nmr_params) + ''' + i];
                }

                ''' + self._cl_func_name + '''(x);

                for(int i = 0; i < ''' + str(self._nmr_params) + '''; i++){
                    x_global[gid * ''' + str(self._nmr_params) + ''' + i] = x[i];
                }
            }
        '''
        return kernel_source