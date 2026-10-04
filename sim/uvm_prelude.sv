//------------------------------------------------------------------------------
// AId-VO compilation-unit prelude  --  NOT part of the testbench.
//
// The provided UVM testbench sources contain no `import uvm_pkg::*;` and no
// `include "uvm_macros.svh"` (their original flow compiled them through a
// simulator project file).  AId-VO compiles this prelude FIRST inside the
// SAME compilation unit (vlog -mfcu), which makes the UVM package and the UVM
// macros visible to every testbench file that follows - WITHOUT modifying a
// single testbench source file.
//
// Strict Non-Modification Rule: this file lives under sim/ and is the only
// SystemVerilog file added by AId-VO.  Nothing under RTL/ or dv/ is ever
// touched by the platform.
//------------------------------------------------------------------------------
`include "uvm_macros.svh"

import uvm_pkg::*;
