from __future__ import with_statement
from rpython.rlib import jit
from type_wrapper import String, Integer, Float, Ptr, List,\
                         Value, NoValue, NumericValue, BasicBlock
from llvm_objects import W_Module
from state import State
from rpython.rtyper.lltypesystem import rffi, lltype

import llvm_wrapper as llwrap
import sys

def target(*args):
    return main, None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

jit_driver = jit.JitDriver(greens=["self", "block", "function"],
                           reds=[])

class NoSuchVariableException(Exception):
    pass

class InvalidFileException(Exception):
    pass

class UnparsableBitcodeException(Exception):
    pass

class Interpreter(object):

    def __init__(self, module, global_state, constants):
        self.module = module
        self.global_state = global_state
        self.constants = constants
        self.last_block = None

    def _get_args(self, args):
        ''' Returns a list of arguments. '''

        arg_vals = []
        for arg in args:
            arg_vals.append(self.lookup_var(arg))
        return arg_vals

    def exit_not_implemented(self, name):
        print "[ERROR]: Found unimplemented operation. Exiting."
        raise NotImplementedError(name)

    def puts(self, string, args=[]):
        print string
        if args:
            for arg in args:
                assert isinstance(arg, NumericValue)
                print arg.value
            print "\n\n"

    def lookup_var(self, var):
        ''' Returns the value of a variable. First checks locals, then globals. '''

        addr = rffi.cast(rffi.INT, var)
        if self.frame.has_key(addr):
            return self.frame.get_variable(addr)
        elif self.global_state.has_key(addr):
            return self.global_state.get_variable(addr)
        elif self.constants.has_key(addr):
            return self.constants.get_variable(addr)
        else:
            print "[ERROR]: Unknown variable. Exiting."
            raise NoSuchVariableException(rffi.charp2str(llwrap.LLVMPrintValueToString(var)))
        return NoValue()

    def get_phi_result(self, function, instruction):
        ''' Returns the result of a given phi instruction. '''

        for i in range(instruction.count_incoming):
            l_block = instruction.incoming_block[i]
            block = function.get_block(l_block)
            if block == self.last_block:
                return self.lookup_var(instruction.incoming_value[i])

    def get_switch_block(self, function, args):
        ''' Returns the block a switch instruction branches to. '''

        cond = self.lookup_var(args[0])
        default_branch = args[1]
        assert isinstance(cond, Integer)
        for i in range(2, len(args), 2):
            switch_var = self.lookup_var(args[i])
            assert isinstance(switch_var, Integer)
            if cond.value == switch_var.value:
                return BasicBlock(function.get_block(args[i + 1]))
        return BasicBlock(function.get_block(default_branch))

    def set_var(self, var, new_value):
        ''' Changes the value of an existing variable. '''

        assert isinstance(new_value, Value)
        addr = rffi.cast(rffi.INT, var)
        if self.frame.has_key(addr):
            self.frame.set_variable(addr, new_value)
        elif self.global_state.has_key(addr):
            self.global_state.set_variable(addr, new_value)
        else:
            print "[ERROR]: Unknown variable. Exiting."
            raise NoSuchVariableException(rffi.charp2str(llwrap.LLVMPrintValueToString(var)))

    def has_function(self, function):
        ''' Return true if the file being interpreted contains a given function,
            false otherwise. '''

        if rffi.cast(rffi.INT, function) in self.functions:
            return True
        return False

    def eval_condition(self, predicate, val1, val2):
        ''' Returns the wrapped boolean result of the comparison of the values of
            the two arguments, according to an ICmp predicate. '''

        assert isinstance(val1, Integer) and isinstance(val2, Integer)
        if predicate == llwrap.LLVMIntSLT:
            return Integer(val1.value < val2.value)
        elif predicate == llwrap.LLVMIntSLE:
            return Integer(val1.value <= val2.value)
        elif predicate == llwrap.LLVMIntEQ:
            return Integer(val1.value == val2.value)
        elif predicate == llwrap.LLVMIntNE:
            return Integer(val1.value != val2.value)
        elif predicate == llwrap.LLVMIntSGT:
            return Integer(val1.value > val2.value)
        elif predicate == llwrap.LLVMIntSGE:
            return Integer(val1.value >= val2.value)
        else:
            self.exit_not_implemented("Unknown ICmp predicate %d" % predicate)

    def exec_operation(self, function, instruction):
        opcode = instruction.opcode
        args = instruction.l_operands
        if opcode == llwrap.LLVMRet:
            if len(args) == 0:
                return NoValue()
            else:
                return self.lookup_var(args[0])
        elif opcode == llwrap.LLVMAdd:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(x.value + y.value)
        elif opcode == llwrap.LLVMFAdd:
            x, y = self._get_args(args)
            assert isinstance(x, Float) and isinstance(y, Float)
            return Float(x.value + y.value)
        elif opcode == llwrap.LLVMMul:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(x.value * y.value)
        elif opcode == llwrap.LLVMFMul:
            x, y = self._get_args(args)
            assert isinstance(x, Float) and isinstance(y, Float)
            return Float(x.value * y.value)
        elif opcode == llwrap.LLVMSub:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(x.value - y.value)
        elif opcode == llwrap.LLVMFSub:
            x, y = self._get_args(args)
            assert isinstance(x, Float) and isinstance(y, Float)
            return Float(x.value - y.value)
        elif opcode == llwrap.LLVMSDiv:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(x.value / y.value)
        elif opcode == llwrap.LLVMFDiv:
            x, y = self._get_args(args)
            assert isinstance(x, Float) and isinstance(y, Float)
            return Float(x.value / y.value)
        elif opcode == llwrap.LLVMSRem:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(int(x.value) % int(y.value))
        elif opcode == llwrap.LLVMAnd:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(int(x.value) & int(y.value))
        elif opcode == llwrap.LLVMOr:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(int(x.value) | int(y.value))
        elif opcode == llwrap.LLVMXor:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(int(x.value) ^ int(y.value))
        elif opcode == llwrap.LLVMShl:
            x, y = self._get_args(args)
            assert isinstance(x, Integer) and isinstance(y, Integer)
            return Integer(int(x.value) << int(y.value))
        elif opcode == llwrap.LLVMCall:
            if self.module.has_function(args[-1]):
                for index in range(instruction.func_param_count):
                    param = instruction.l_func_params[index]
                    self.global_state.set_variable(rffi.cast(rffi.INT, param),\
                                                   self.lookup_var(args[index]))
                interp_fun = Interpreter(self.module, self.global_state, self.constants)
                func = self.module.get_function(args[-1])
                return interp_fun.run(func)
            else:
                string_format_ref = instruction.l_string_format_ref
                str_var = self.lookup_var(string_format_ref)
                assert isinstance(str_var, String)
                string_format = str_var.value
                fn_name = instruction.func_name
                if fn_name == "printf" or fn_name == "puts":
                    printf_args = []
                    for i in range(1, len(args) - 1):
                        arg = args[i]
                        var = self.lookup_var(arg)
                        printf_args.append(var)
                    self.puts(string_format, printf_args)
                else:
                    self.exit_not_implemented(fn_name)
        elif opcode == llwrap.LLVMAlloca:
            return Ptr(lltype.scoped_alloc(rffi.VOIDP.TO, 1))
        elif opcode == llwrap.LLVMStore:
            # store arg[0] in arg[1]
            var = self.lookup_var(args[0])
            self.set_var(args[1], var)
        elif opcode == llwrap.LLVMLoad:
            return self.lookup_var(args[0])
        elif opcode == llwrap.LLVMFPExt:
            # extend a floating point value (eg float -> double)
            var_val = self.lookup_var(args[0])
            assert isinstance(var_val, Float)
            return Float(var_val.value)
        elif opcode == llwrap.LLVMZExt:
            var_val = self.lookup_var(args[0])
            assert isinstance(var_val, Integer)
            return Integer(var_val.value)
        elif opcode == llwrap.LLVMFPTrunc:
            # truncate a floating point value (double -> float)
            var_val = self.lookup_var(args[0])
            assert isinstance(var_val, Float)
            return Float(var_val.value)
        elif opcode == llwrap.LLVMSIToFP:
            # convert Signed to Floating Point
            var_val = self.lookup_var(args[0])
            assert isinstance(var_val, Integer)
            return Float(float(var_val.value))
        elif opcode == llwrap.LLVMBr:
            # if the jump is conditional, it's necessary to find
            # the block to jump to
            if instruction.is_conditional():
                cond = self.lookup_var(instruction.condition)
                assert isinstance(cond, Integer)
                if cond.value == True:
                    return BasicBlock(function.get_block(instruction.l_bb_true))
                else:
                    return BasicBlock(function.get_block(instruction.l_bb_false))
            else:
                # unconditional jump
                return BasicBlock(function.get_block(instruction.l_bb_uncond))
        elif opcode == llwrap.LLVMICmp:
            val1 = self.lookup_var(args[0])
            val2 = self.lookup_var(args[1])
            predicate = instruction.icmp_predicate
            return self.eval_condition(predicate, val1, val2)
        elif opcode == llwrap.LLVMPHI:
            return self.get_phi_result(function, instruction)
        elif opcode == llwrap.LLVMSelect:
            cond = self.lookup_var(args[0])
            assert isinstance(cond, Integer)
            if cond.value != 0:
                return self.lookup_var(args[1])
            else:
                return self.lookup_var(args[2])
        elif opcode == llwrap.LLVMSwitch:
            return self.get_switch_block(function, args)
        else:
            self.exit_not_implemented("Unknown opcode %d" % opcode)
        return NoValue()

    def run(self, function):
        self.frame = State()
        block = function.get_first_block()
        while block:
            jit_driver.jit_merge_point(function=function, block=block, self=self)
            last_block_loc = self.last_block
            instruction = block.get_first_instruction()
            next_block = block.w_next_block
            while instruction:
                result = self.exec_operation(function, instruction)
                if isinstance(result, BasicBlock):
                    next_block = result.value
                    break
                elif not isinstance(result, NoValue):
                    self.frame.set_variable(instruction.addr, result)
                instruction = instruction.w_next_instr
                # last instruction should be ret
                if not instruction:
                    return result
            self.last_block = block
            block = next_block

def create_module(filename):
    ''' Returns the module created with the contents of the given file
        as a W_Module object. '''

    module = llwrap.LLVMModuleCreateWithName("module")
    with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as out_message:
        with lltype.scoped_alloc(rffi.VOIDP.TO, 1) as mem_buff:
            with lltype.scoped_alloc(rffi.VOIDPP.TO, 1) as mem_buff_ptr:
                mem_buff_ptr[0] = mem_buff
                rc = llwrap.LLVMCreateMemoryBufferWithContentsOfFile(filename, mem_buff_ptr, out_message)
                if rc != 0:
                    print"[ERROR]: Cannot create memory buffer with contents of"\
                         " %s: %s.\n" % (filename, rffi.charp2str(out_message[0]))
                    raise InvalidFileException(filename)
                mem_buff = mem_buff_ptr[0]

            with lltype.scoped_alloc(rffi.VOIDPP.TO, 1) as module_ptr:
                module_ptr[0] = module
                rc = llwrap.LLVMParseBitcode(mem_buff, module_ptr, out_message)
                if rc != 0:
                    print "[ERROR]: Cannot parse %s: %s.\n" % (filename, rffi.charp2str(out_message[0]))
                    raise UnparsableBitcodeException(filename)
                module = module_ptr[0]
    return W_Module(module)

def main(args):
    if len(args) < 2:
        print"[ERROR]: Need an argument:\nUsage: ./llvmtest name.bc [C args]\n"
        return 1
    module = create_module(args[1])
    main_argc = len(args) - 1
    main_argv = args[1:]
    global_state = State()
    module.load_globals(global_state, main_argc, main_argv)
    interp = Interpreter(module, global_state, module.constants)
    interp.run(module.w_main_fun)
    return 0

if __name__ == '__main__':
   main(sys.argv)
