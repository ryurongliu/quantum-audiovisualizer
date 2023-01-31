import maxpy as mp


def make_freqs(num_components, num_states):
    """
    Make a set of frequencies of size num_states within an octave, using num_components to find starting pitch. 
    """
    
    starting_freq = 200. + num_components * 10
    freqs = [starting_freq]
    for i in range(1, num_states+1):
        freqs.append(starting_freq * 2**(i/num_states))
    
    return freqs


def get_waiting_seq(freqs, expected_probabilities, states, slide_f, slide_t, amb_length):
    
    """
    Get ambient and oversound sequences for waiting music.
    
    Iterate through states. 
        For ambient, add that state's note once for each 1/16 of expected probability.
        For oversounds, play that state's collection of sounds staggered across
        the total length of ambient notes for that state. 
    
    """
    
    ambient_seq = []
    oversound_seq = []

    #for each state
    for i in range(len(states)):
        
        prob = expected_probabilities[i]
        state = states[i]
        freq = freqs[i]
        
        #if probability is zero, skip this state
        if prob == 0:
            continue
        
        #how many times to play this ambient note
        num_ambient_notes = int(prob / (100 / 16))
        #message for ambient sequence
        ambient_info = str(freq-slide_f ) + " " + str(freq) + " " + str(slide_t)
        
        #add ambient notes to sequence
        for j in range(num_ambient_notes):
            ambient_seq.append([ambient_info, amb_length, "ambient"])

            
        num_oversounds = len(state)
        #if no oversounds, go on to next state
        if num_oversounds == 0:
            continue
        
        #find out how much time each oversound gets
        total_time = amb_length * num_ambient_notes
        time_per_oversound = total_time / len(state)
        
        for oversound in state:
            if oversound == "gloop":
                oversound_seq.append([oversound, time_per_oversound, "oversound", freq])
            else:
                oversound_seq.append([oversound, time_per_oversound, "oversound"])

    return ambient_seq, oversound_seq


def get_color(num_comps):
    """
    Get ambient "color" setting from number of components.
    """
    color = 350 + 700/num_comps
    return None







##########################################################################
#############    AMBIENT SYNTH BUILDING FUNCTIONS     #####################
##########################################################################

def build_ambient_synth(num_comps, ambient_filename):
    
    """
    Build the ambient synth, adding oscillator chains for each component.
    """
    
    #get osc info
    num_oscs = get_num_ambient_oscs(num_comps)
    
    osc_freq_exprs = get_ambient_osc_freq_exprs(num_oscs)
    osc_pan_exprs = get_ambient_osc_pan_exprs(num_oscs)

    #make osc patches
    osc_objs = []
    for i in range(num_oscs):
        osc = mp.MaxPatch(load_file="osc-to-add.maxpat", verbose=False)
        pan_expr = osc.objs['obj-3']
        freq_expr = osc.objs['obj-9']
        pan_expr.edit(text=osc_pan_exprs[i], text_add="replace")
        freq_expr.edit(text=osc_freq_exprs[i], text_add="replace")

        filename = "osc-to-add-" + str(i)
        osc.save("osc-to-add-" + str(i), verbose=False, check=False)
        osc_objs.append(filename)

    #open ambient patch
    ambient = mp.MaxPatch(load_file = "ambient-dynamic-template.maxpat", verbose=False)
    #get objs in ambient patch
    dial = None
    freqnum = None
    env = None
    loadbang = None
    snapshot = None
    bottom = None
    for key, val in ambient.objs.items():
        if val.name == "dial":
            dial = val
        elif val.name == "flonum":
            freqnum = val
        elif val.name == "function":
            env = val
        elif val.name == "loadbang":
            loadbang = val
        elif val.name == "snapshot~":
            snapshot = val
        elif val.name == "ambient-bottom":
            bottom = val

    ambient.set_position(0, 700)
    #for each osc, place and connect
    for osc_name in osc_objs:
        osc = ambient.place([osc_name], verbose=False)[0]
        ambient.connect((dial.outs[0], osc.ins[0]),
                        (freqnum.outs[0], osc.ins[1]),
                        (loadbang.outs[0], osc.ins[2]),
                        (env.outs[1], osc.ins[3]),
                        (snapshot.outs[0], osc.ins[4]),
                        (osc.outs[0], bottom.ins[0]),
                        (osc.outs[1], bottom.ins[1]), verbose=False)

    #save ambient patch
    ambient.save(ambient_filename, verbose=False, check=False)
    
    
def get_num_ambient_oscs(num_components):
    """
    Get the number of ambient oscillators from number of components. 
    """
    if num_components < 4:
        return 4
    
    elif num_components %2 == 1:
        return num_components - 1
    else:
        return num_components


def get_ambient_osc_freq_exprs(num_oscs):
    """
    Get frequency shifts of each oscillator. 
    """
    right_side = []
    left_side = []
    mult_order = [1., 2., 0.5]
    for i in range(int(num_oscs/2)):
        add_mult = i % 6 + 1
        
        right_mult = mult_order[i%3]
        expr_right = "$f1*" + str(right_mult) + " + $f2*" + str(add_mult)
        right_side.append(expr_right)
        
        left_mult = mult_order[(i+1)%3]
        expr_left = "$f1*" + str(left_mult) + " - $f2*" + str(add_mult)
        left_side.insert(0, expr_left)
    return left_side + right_side

def get_ambient_osc_pan_exprs(num_oscs):
    """
    Get pan ranges of each oscilator. 
    """
    right_side = []
    left_side = []
    
    for i in range(int(num_oscs/2)):
        expr_right = "64. + $f1*" + str(float(i+1)) + "/" + str(float(num_oscs))
        expr_left = "64. - $f1*" + str(float(i+1)) + "/" + str(float(num_oscs))
        right_side.append(expr_right)
        left_side.insert(0, expr_left)
    return left_side + right_side


##########################################################################
#############    SEQUENCER BUILDING FUNCTIONS     #####################
##########################################################################

def create_amb_seq_patch(ambient_sequence, filename):
    
    """
    Build sequencer patch from ambient sequence.
    """

    amb_seq = mp.MaxPatch(load_file = "sel-patch.maxpat", verbose=False)
    amb_seq.set_position(20, 600)
    
    sel = amb_seq.objs['obj-11']
    output = amb_seq.place(['outlet'])[0]
    route = amb_seq.place(["route message"])[0]
    
    amb_seq.set_position(20, 400)
    
    for i in range(len(ambient_sequence)):
        msg = amb_seq.place(['message ' + ambient_sequence[i][0]])[0]
        amb_seq.connect((sel.outs[i], msg.ins[0]),verbose=False)
        amb_seq.connect((msg.outs[0], route.ins[0]),verbose=False)
        
    amb_seq.connect((route.outs[0], output.ins[0]),verbose=False)
    
    amb_seq.save(filename, verbose=False)
    return



def create_over_seq_patch(over_seq, filename):
    
    """
    Build oversound patch from oversound sequence.
    """
    #load in template patch
    over_seq_patch = mp.MaxPatch(load_file = "over-seq-template.maxpat", verbose=False)
    
    #get relevant objects
    msg = over_seq_patch.objs['obj-3']
    gate = over_seq_patch.objs['obj-19']
    back_outlet = over_seq_patch.objs['obj-17']
    gloop_outlet = over_seq_patch.objs['obj-16']
    gloopfreq_outlet = over_seq_patch.objs['obj-15']
    glitch_outlet = over_seq_patch.objs['obj-14']
    gran_outlet = over_seq_patch.objs['obj-13']

    outlet_map = {
        "back": back_outlet,
        "glitch": glitch_outlet,
        "gran": gran_outlet
    }
    
    #place and connect counter and sel
    num_overnotes = len(over_seq)
    over_seq_patch.set_position(150, 265)
    counter = over_seq_patch.place(["counter " + str(num_overnotes) + " 1"], verbose=False)[0]

    sel_str = "sel"
    for i in range(num_overnotes):
        sel_str += " " + str(i+1)
    over_seq_patch.set_position(150, 300)
    sel = over_seq_patch.place([sel_str], verbose=False)[0]

    over_seq_patch.connect((gate.outs[0], counter.ins[0]), 
                           (msg.outs[0], counter.ins[2]), 
                           (counter.outs[0], sel.ins[0]), verbose=False)
    
    
    #place trigger/delay(/messaage) objects for each note
    for i in range(num_overnotes):
        note = over_seq[i]
        sound = note[0]
        delay_time = note[1] * 1000

        #deal with gloop connections
        if sound == "gloop":
            #place trigger and delay
            trigger = over_seq_patch.place(["t b b b"], verbose=False)[0]
            #place delay
            delay = over_seq_patch.place(["delay " + str(delay_time)], verbose=False)[0]

            #place freq msg and route
            freq = note[3]
            freq_msg = over_seq_patch.place(["message " + str(freq)], verbose=False)[0]
            freq_route = over_seq_patch.place(["route message"], verbose=False)[0]


            #connect everything
            over_seq_patch.connect((sel.outs[i], trigger.ins[0]),
                                   (trigger.outs[0], delay.ins[0]),
                                   (trigger.outs[1], gloop_outlet.ins[0]),
                                   (trigger.outs[2], freq_msg.ins[0]),
                                   (freq_msg.outs[0], freq_route.ins[0]),
                                   (freq_route.outs[0], gloopfreq_outlet.ins[0]),
                                   (delay.outs[0], gate.ins[1]), verbose=False)

        else:
            #place trigger
            trigger = over_seq_patch.place(["t b b"], verbose=False)[0]
            #place delay
            delay = over_seq_patch.place(["delay " + str(delay_time)], verbose=False)[0]

            #connect everything
            over_seq_patch.connect((sel.outs[i], trigger.ins[0]),
                                   (trigger.outs[1], outlet_map[sound].ins[0]),
                                   (trigger.outs[0], delay.ins[0]),
                                   (delay.outs[0], gate.ins[1]), verbose=False)
     
    over_seq_patch.save(filename, verbose=False)
    