#!/usr/bin/env python3
"""Plots for ../README.md, from results/sparams_{lossless,lossy}.npz.

plots/fitted_material.png: eps' and tan d of the fitted Debye model against the stackup values
plots/extra_loss.png:      extra loss from tan d, simulated against the textbook formula
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from gds2openEMS import util_debye_fit

C0 = 2.99792458e8
EPS_R, TAND = 4.3, 0.02          # FR4 in FR4_microstrip_lossy.xml
FSTART, FSTOP = 1e9, 4e9         # settings['fstart'], settings['fstop'] of the model
L = 0.1                          # line length, m

INK, MUTED, GRID = '#17212b', '#5b6875', '#e3e8ec'
SIM, REF = '#c4462f', '#2b6c9e'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.8, 'axes.spines.top': False,
                     'axes.spines.right': False, 'legend.frameon': False,
                     'axes.titlesize': 11, 'axes.titlecolor': INK, 'axes.titleweight': 'bold'})

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, 'plots')
os.makedirs(out_dir, exist_ok=True)


def debye_model(f):
    eps_inf, poles = util_debye_fit.fit_wideband_debye(EPS_R, TAND, FSTART, FSTOP)
    w = 2 * np.pi * f
    eps = eps_inf + sum(de / (1 + 1j * w * tau) for de, tau in poles)
    return eps.real, -eps.imag / eps.real


def eps_eff(f, s21):
    """ effective permittivity of the line from the S21 phase """
    phi = np.unwrap(np.angle(s21))
    phi -= 2 * np.pi * np.round(np.polyfit(f, phi, 1)[1] / (2 * np.pi))   # phase -> 0 at f = 0
    return (-phi * C0 / (2 * np.pi * f * L)) ** 2


# fitted material over a wide range, simulated band marked
f = np.logspace(8, 10.6, 400)
er, td = debye_model(f)
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, y, target, label in ((axs[0], er, EPS_R, "ε′"), (axs[1], td, TAND, 'tan δ')):
    ax.axvspan(FSTART / 1e9, FSTOP / 1e9, color=GRID, alpha=0.6, lw=0, label='simulated band')
    ax.plot(f / 1e9, y, color=SIM, lw=1.8, label='Debye model in openEMS')
    ax.axhline(target, color=REF, lw=1.4, ls='--', label='stackup value')
    ax.set_xscale('log')
    ax.set(xlabel='Frequency (GHz)', ylabel=label, title=f'{label} of the FR4')
axs[0].set_ylim(4.0, 4.6)
axs[1].set_ylim(0, 0.03)
axs[1].legend(loc='lower center', fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(out_dir, 'fitted_material.png'), dpi=150, facecolor='white')
plt.close(fig)

# extra loss from tan d: simulated (lossy - lossless) against the textbook formula
lossless = np.load(os.path.join(here, 'sparams_lossless.npz'))
lossy = np.load(os.path.join(here, 'sparams_lossy.npz'))
f = lossless['f']
db = lambda x: 20 * np.log10(np.abs(x))
extra = db(lossless['s21']) - db(lossy['s21'])
ee = eps_eff(f, lossless['s21'])
k0 = 2 * np.pi * f / C0
alpha_d = k0 * EPS_R * (ee - 1) * TAND / (2 * np.sqrt(ee) * (EPS_R - 1))     # Np/m, Pozar
textbook = 8.686 * alpha_d * L

fig, ax = plt.subplots(figsize=(7, 3.8))
ax.plot(f / 1e9, textbook, color=REF, lw=1.8, ls='--', label='textbook formula (Pozar)')
ax.plot(f / 1e9, extra, color=SIM, lw=1.8, label='openEMS, lossy minus lossless')
ax.set(xlabel='Frequency (GHz)', ylabel='Extra loss (dB)', xlim=(1, 4), ylim=(0, None),
       title='Extra loss from tan δ = 0.02 over 100 mm')
ax.legend(loc='upper left')
fig.tight_layout()
fig.savefig(os.path.join(out_dir, 'extra_loss.png'), dpi=150, facecolor='white')
plt.close(fig)

dev = 100 * (extra / textbook - 1)
print(f'extra loss vs textbook: {dev.min():+.1f} .. {dev.max():+.1f} %')
for x in (1e9, 2e9, 3e9, 4e9):
    i = np.argmin(abs(f - x))
    print(f'  {f[i]/1e9:.0f} GHz: openEMS {extra[i]:.3f} dB, textbook {textbook[i]:.3f} dB')
print('Wrote', out_dir)
