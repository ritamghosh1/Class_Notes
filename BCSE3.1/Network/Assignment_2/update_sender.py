import re

with open("sender.py", "r") as f:
    content = f.read()

# 1. Add import
content = content.replace("from timer          import FrameTimer", 
                          "from timer          import FrameTimer\nfrom dashboard      import Dashboard, NullDashboard")

# 2. Add --dashboard arg
content = content.replace('help="Print per-frame details")',
                          'help="Print per-frame details")\n    parser.add_argument("--dashboard", action="store_true",\n                        help="Enable rich terminal dashboard")')

# 3. Initialize dashboard
dash_init = """
    # --- Connect to receiver ---
    sock = create_client_socket(args.host, args.port)
    ch   = Channel(sock,
                   p_error      = args.p_error,
                   p_loss       = args.p_loss,
                   max_delay_ms = args.delay,
                   label        = "SENDER")

    # --- Setup Dashboard ---
    if args.dashboard:
        # We need total_frames for the dashboard progress bar
        # Easiest way is to count chunks here, though protocols do it too.
        # But let's just pass 100 as default or read file size.
        import os
        try:
            total_size = os.path.getsize(args.input)
            total_frames_est = max(1, (total_size + args.payload - 1) // args.payload)
        except Exception:
            total_frames_est = 100
            
        dash = Dashboard(protocol=args.protocol, window_size=args.window, 
                         total_frames=total_frames_est, host=args.host, 
                         port=args.port, role="SENDER")
    else:
        dash = NullDashboard()
"""
content = re.sub(r'# --- Connect to receiver ---.*label\s*=\s*"SENDER"\)', dash_init.strip(), content, flags=re.DOTALL)

# 4. Pass dash to protocols
content = content.replace("m = run_saw_sender(ch, args.input, args.payload,\n                           args.timeout, args.verbose)",
                          "m = run_saw_sender(ch, args.input, args.payload,\n                           args.timeout, args.verbose, dash)")
content = content.replace("m = run_gbn_sender(ch, args.input, args.payload,\n                           args.window, args.timeout, args.verbose)",
                          "m = run_gbn_sender(ch, args.input, args.payload,\n                           args.window, args.timeout, args.verbose, dash)")
content = content.replace("m = run_sr_sender(ch, args.input, args.payload,\n                          args.window, args.timeout, args.verbose)",
                          "m = run_sr_sender(ch, args.input, args.payload,\n                          args.window, args.timeout, args.verbose, dash)")


with open("sender.py", "w") as f:
    f.write(content)
