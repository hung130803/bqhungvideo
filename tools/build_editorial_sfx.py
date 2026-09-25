"""Original procedural accents. Reproducible, no downloaded samples."""
import argparse,tempfile,wave,subprocess
from pathlib import Path
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'app/assets/sfx'
    recipes=[('pop','bubble',.3,880),('pop','wood_tap',.2,420),
      ('reveal','glass_chime',1.1,1200),('reveal','soft_resolve',1.4,660),
      ('impact','muted_hit',.45,85),('impact','knock',.25,210),
      ('suspense','heartbeat',1.2,65),('suspense','clock',1.3,950),
      ('comedy','rubber',.6,220),('comedy','descending',.65,720),
      ('transition','brush',.45,400),('transition','short_air',.25,500),
      ('riser','tension_swell',1.4,180),('riser','reverse_chime',.9,880),
      ('sad','low_bell',1.5,220),('sad','soft_fall',1.2,440),
      ('scratch','tape_stop',.6,300),('scratch','shutter',.25,1000),
      ('drumroll','soft_roll',.9,130),('drumroll','three_taps',.7,360)]
    rng=np.random.default_rng(1650);sr=48000
    with tempfile.TemporaryDirectory(prefix='bq_sfx_build_') as folder:
        for cat,name,seconds,freq in recipes:
            t=np.arange(int(sr*seconds))/sr;noise=rng.standard_normal(len(t));decay=np.exp(-t*6/seconds)
            tone=np.sin(2*np.pi*freq*t);signal=tone*decay
            if name in ('glass_chime','soft_resolve','low_bell'):
                signal=(tone+.4*np.sin(2*np.pi*freq*1.5*t)+.2*np.sin(2*np.pi*freq*2.01*t))*decay
            elif name in ('muted_hit','knock','wood_tap','three_taps','soft_roll','heartbeat','clock','shutter'):
                interval={'three_taps':.21,'soft_roll':.075,'heartbeat':.43,'clock':.5}.get(name,2.)
                pulse=np.exp(-np.mod(t,interval)*55)
                signal=(tone+.22*noise)*pulse
            elif cat in ('transition','riser'):
                smooth=np.convolve(noise,np.ones(9)/9,mode='same')
                env=np.sin(np.pi*t/seconds)**2
                signal=smooth*env if cat=='transition' else (tone*.2+smooth)*env*(t/seconds)
            elif name in ('rubber','descending','soft_fall','tape_stop'):
                end=freq*.2;signal=np.sin(2*np.pi*(freq*t+(end-freq)*t*t/(2*seconds)))*decay
            signal*=np.minimum(1,t/.008)*np.minimum(1,(seconds-t)/.02)
            signal=signal/max(.001,float(np.max(np.abs(signal))))*.32
            path=Path(folder)/'sound.wav'
            with wave.open(str(path),'wb') as stream:
                stream.setparams((1,2,sr,0,'NONE','not compressed'));stream.writeframes((signal*32767).astype('<i2').tobytes())
            out=root/cat/f'ed_{name}.opus';out.parent.mkdir(exist_ok=True)
            subprocess.run([args.ffmpeg,'-y','-v','error','-i',str(path),'-c:a','libopus','-b:a','64k',str(out)],check=True,
                timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    print('Generated 20 original accents.')


if __name__=='__main__':main()
