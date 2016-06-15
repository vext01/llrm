from subprocess import Popen, PIPE

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class CConfig(object):
    _includes = "llvm-c/Core.h llvm-c/BitReader.h"
    output, error = Popen("llvm-config --libs core native --system-libs", 
                    shell=True, stdout=PIPE, stderr=PIPE).communicate()
    # remove -l from each library
    output = [lib[2:] for lib in output.split()]     
    _compilation_info_ = ExternalCompilationInfo(
                            includes=_includes.split(),
                            library_dirs=["/usr/local/lib"],
                            libraries=output,
                            compile_extra=["-g"],
                            link_extra=["-lclang", "-L/usr/local/lib"])

cconfig = rffi_platform.configure(CConfig)
    
LLVMModuleCreateWithName = rffi.llexternal("LLVMModuleCreateWithName", 
                           [rffi.CCHARP], 
                            rffi.VOIDP, 
                            compilation_info=CConfig._compilation_info_)

LLVMPrintModuleToString = rffi.llexternal("LLVMPrintModuleToString", 
                          [rffi.VOIDP], 
                           rffi.CCHARP, 
                           compilation_info=CConfig._compilation_info_)

LLVMPrintValueToString = rffi.llexternal("LLVMPrintValueToString", 
                        [rffi.VOIDP], 
                         rffi.CCHARP, 
                         compilation_info=CConfig._compilation_info_)

# LLVMBool LLVMCreateMemoryBufferWithContentsOfFile(const char *Path, LLVMMemoryBufferRef *OutMemBuf, char **OutMessage)
LLVMCreateMemoryBufferWithContentsOfFile = rffi.llexternal("LLVMCreateMemoryBufferWithContentsOfFile",   
                                           [rffi.CCHARP, rffi.VOIDPP, rffi.CCHARPP],
                                            rffi.INT,
                                            compilation_info=CConfig._compilation_info_)

LLVMParseBitcode = rffi.llexternal("LLVMParseBitcode",
                   [rffi.VOIDP, rffi.VOIDPP, rffi.CCHARPP],
                    rffi.INT,
                    compilation_info=CConfig._compilation_info_)

# LLVMValueRef LLVMGetNamedFunction(LLVMModuleRef M, const char *Name) 	 
LLVMGetNamedFunction = rffi.llexternal("LLVMGetNamedFunction",
                       [rffi.VOIDP, rffi.CCHARP],
                        rffi.VOIDP,
                        compilation_info=CConfig._compilation_info_)

# void LLVMGetBasicBlocks(LLVMValueRef Fn, LLVMBasicBlockRef *BasicBlocks)
LLVMGetBasicBlocks = rffi.llexternal("LLVMGetBasicBlocks",
                     [rffi.VOIDP, rffi.VOIDPP],
                      lltype.Void,
                      compilation_info=CConfig._compilation_info_)

LLVMGetValueName = rffi.llexternal("LLVMGetValueName",
                   [rffi.VOIDP],
                    rffi.CCHARP,
                    compilation_info=CConfig._compilation_info_) 

# LLVMBasicBlockRef LLVMGetFirstBasicBlock(LLVMValueRef Fn) 	 
LLVMGetFirstBasicBlock = rffi.llexternal( "LLVMGetFirstBasicBlock",
                        [rffi.VOIDP],
                         rffi.VOIDP,
                         compilation_info=CConfig._compilation_info_)

# LLVMBasicBlockRef LLVMGetNextBasicBlock(LLVMBasicBlockRef BB) 	 
LLVMGetNextBasicBlock = rffi.llexternal( "LLVMGetNextBasicBlock",
                        [rffi.VOIDP],
                         rffi.VOIDP,
                         compilation_info=CConfig._compilation_info_)

LLVMGetFirstInstruction = rffi.llexternal( "LLVMGetFirstInstruction",
                        [rffi.VOIDP],
                         rffi.VOIDP,
                         compilation_info=CConfig._compilation_info_)

LLVMGetNextInstruction = rffi.llexternal( "LLVMGetNextInstruction",
                        [rffi.VOIDP],
                         rffi.VOIDP,
                         compilation_info=CConfig._compilation_info_)

LLVMGetNumOperands = rffi.llexternal("LLVMGetNumOperands",  
                     [rffi.VOIDP],
                      rffi.INT,
                      compilation_info=CConfig._compilation_info_)

LLVMGetInstructionOpcode = rffi.llexternal("LLVMGetInstructionOpcode",  
                          [rffi.VOIDP],
                           rffi.INT,
                           compilation_info=CConfig._compilation_info_)

LLVMGetOperand = rffi.llexternal("LLVMGetOperand",  
                [rffi.VOIDP, lltype.Unsigned],
                 rffi.VOIDP,
                 compilation_info=CConfig._compilation_info_)

def getReference():
    return lltype.malloc(rffi.VOIDP.TO, 1, flavor="raw")
 

