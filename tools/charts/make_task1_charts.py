"""Redraw Writing Task 1 charts whose source images had site watermarks, logos or data errors.

Values are read from the original charts (or, where the original data was impossible, adjusted as noted).
Run: python3 tools/charts/make_task1_charts.py  -> writes PNGs to tools/assets/
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

OUT = os.path.join(os.path.dirname(__file__), '..', 'assets')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.edgecolor': '#444', 'axes.titleweight': 'bold',
                     'axes.titlesize': 13})
GREYS = ['#3a3a3a', '#7a7a7a', '#b5b5b5', '#dcdcdc', '#ffffff']
COLS = ['#1f4e79', '#c55a11', '#548235', '#7f6000', '#7030a0']


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=130, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def grouped_bars(ax, cats, series, colors, width=0.8, labels=None, hatches=None):
    n = len(series)
    x = np.arange(len(cats))
    w = width / n
    for i, (name, vals) in enumerate(series.items()):
        ax.bar(x - width / 2 + w * (i + 0.5), vals, w, label=name, color=colors[i], edgecolor='#333',
               linewidth=0.6, hatch=hatches[i] if hatches else None)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.yaxis.grid(True, color='#ddd', linewidth=0.8)
    ax.set_axisbelow(True)


def pie(ax, vals, labels, colors, title, hatches=None):
    wedges, _ = ax.pie(vals, colors=colors, startangle=90, counterclock=False,
                       wedgeprops={'edgecolor': '#333', 'linewidth': 0.8})
    if hatches:
        for w, h in zip(wedges, hatches):
            w.set_hatch(h)
    for w, v in zip(wedges, vals):
        ang = np.deg2rad((w.theta1 + w.theta2) / 2)
        r = 0.68 if v >= 8 else 1.15
        ax.text(r * np.cos(ang), r * np.sin(ang), f'{v}%', ha='center', va='center', fontsize=11,
                bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85) if v >= 8 else None)
    ax.set_title(title, fontsize=12)
    ax.set_aspect('equal')
    return wedges


# Mock 9: three titled pies (the source had no titles, an identical consumption and profit pie,
# and "explorer" for exporter); production data kept, the other two rebuilt with plausible figures
def mock9():
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 5))
    c = ['#5b3a1e', '#8c5a2b', '#b9834f', '#dcb48a', '#f1e0cc']
    sets = [('Coffee production', [19, 44, 17, 18, 2], ['Africa', 'South America', 'Central America', 'Asia', 'Oceania']),
            ('Coffee consumption', [34, 27, 18, 12, 9], ['Europe', 'North America', 'Asia', 'South America', 'Other']),
            ('Share of profit from coffee', [7, 11, 27, 55], ['Producers (farmers)', 'Exporters', 'Shippers', 'Sellers (retail)'])]
    for ax, (t, v, l) in zip(axs, sets):
        w = pie(ax, v, l, c[:len(v)], t)
        ax.legend(w, l, loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False, fontsize=10)
    fig.suptitle('World coffee: production, consumption and distribution of profit', fontweight='bold', fontsize=14)
    save(fig, 'mock09_task1.png')


# Mock 12: "Belguim" and "pounds string" in the source
def mock12():
    cats = ['Console\ngames', 'Outdoor game\naccessories', 'Cosmetics', 'Books', 'Toys', 'Cameras']
    s = {'Belgium': [147, 150, 147, 144, 147, 145], 'Spain': [150, 154, 154, 154, 158, 156],
         'Austria': [146, 142, 144, 158, 158, 166], 'Britain': [156, 157, 160, 162, 168, 170]}
    fig, ax = plt.subplots(figsize=(10, 5.6))
    grouped_bars(ax, cats, s, ['#e46c0a', '#a50021', '#1f3864', '#548235'])
    ax.set_ylim(125, 175)
    ax.set_yticks(range(125, 176, 5))
    ax.set_ylabel('Thousand pounds sterling')
    ax.set_title('Amount spent on consumer goods, 2012')
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), frameon=False)
    save(fig, 'mock12_task1.png')


# Mock 29: watermark and "Activate Windows" text in the source
def mock29():
    cats = ['Sales', 'Accounting', 'Computing', 'Nursing', 'Farming']
    s = {'2001': [156000, 67000, 58000, 56000, 29000], '2008': [166000, 58000, 78000, 60000, 18000]}
    fig, ax = plt.subplots(figsize=(9, 5.4))
    grouped_bars(ax, cats, s, ['#bdbdbd', '#555555'], width=0.6)
    ax.set_ylim(0, 180000)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v):,}'))
    ax.set_ylabel('Number of people employed')
    ax.set_title('People employed in five types of work in one region of Australia, 2001 and 2008')
    ax.legend(frameon=False)
    save(fig, 'mock29_task1.png')


def mock30():
    years = ['2004', '2005', '2006', '2007', '2008']
    s = {'China': [28000, 21200, 17300, 17300, 15400], 'Japan': [6200, 6200, 7400, 9200, 10200],
         'USA': [13200, 15400, 17300, 22300, 27800], 'Russia': [2700, 2100, 2100, 2100, 3100]}
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    grouped_bars(ax, years, s, ['#d9534f', 'white', '#f4b183', 'white'], hatches=[None, '..', '////', None])
    ax.set_ylim(0, 30000)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v):,}'))
    ax.set_ylabel('Number of applicants')
    ax.set_title('International applicants to the universities of one European country (2004-2008)')
    ax.legend(ncol=4, loc='upper center', bbox_to_anchor=(0.5, -0.08), frameon=False)
    save(fig, 'mock30_task1.png')


def table(name, title, header, rows, colw=None):
    fig, ax = plt.subplots(figsize=(10, 0.6 + 0.55 * (len(rows) + 1)))
    ax.axis('off')
    t = ax.table(cellText=rows, colLabels=header, loc='center', cellLoc='center', colWidths=colw)
    t.auto_set_font_size(False)
    t.set_fontsize(11)
    t.scale(1, 2.0)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor('#555')
        if r == 0:
            cell.set_facecolor('#d9d9d9')
            cell.set_text_props(weight='bold')
    ax.set_title(title, fontweight='bold', pad=8)
    save(fig, name)


def mock31():
    table('mock31_task1.png', "Percentage of first-year students rating aspects of their course 'very good'",
          ['Course', 'Pre-course\ninformation', 'Teaching\nquality', 'Tutor\nsupport', 'Resources\n(print)', 'Resources\n(other)'],
          [['Economics', '55%', '95%', '92%', '59%', '62%'],
           ['Law', '72%', '67%', '79%', '70%', '80%'],
           ['Commerce', '95%', '95%', '93%', '81%', '86%']])


def two_pies(name, title, years, data, labels, hatches=None):
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.6))
    cols = ['#404040', 'white', '#8c8c8c', '#f2f2f2', '#bfbfbf']
    for ax, y, v in zip(axs, years, data):
        w = pie(ax, v, labels, cols[:len(v)], y, hatches)
    fig.legend(w, labels, loc='lower center', ncol=3, frameon=False, fontsize=10)
    fig.suptitle(title, fontweight='bold', fontsize=14)
    fig.subplots_adjust(bottom=0.2, top=0.82)
    save(fig, name)


# Mock 32: brand logo in the source
def mock32():
    two_pies('mock32_task1.png', 'Main reasons why students chose a college or university, UK',
             ['1987', '2007'], [[21, 35, 10, 15, 19], [17, 37, 22, 18, 6]],
             ['Quality of resources', 'Suitable degree courses', 'Close to parental home', 'Quality of teaching',
              'Good sports and social activities'], [None, '////', '..', None, '--'])


# Mock 33: the source repeated mock 32's data, so this mock now has a task of its own
def mock33():
    two_pies('mock33_task1.png', 'How students at one UK university spent their weekly budget',
             ['1997', '2007'], [[38, 25, 10, 12, 15], [45, 20, 12, 6, 17]],
             ['Accommodation', 'Food', 'Transport', 'Books and course materials', 'Entertainment'],
             [None, '////', '..', None, '--'])


def mock34():
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 5))
    labels = ['0-15 years', '16-24 years', '25-34 years', '35-54 years', '55+ years']
    cols = ['#5bc0de', '#2e5c8a', '#3cb371', '#f0884a', '#f7c35f']
    for ax, y, v in zip(axs, ['1983', '2003'], [[10, 4, 20, 50, 16], [12, 15, 12, 35, 26]]):
        w = pie(ax, v, labels, cols, y)
    fig.legend(w, labels, loc='lower center', ncol=5, frameon=False)
    fig.suptitle('Age of visitors from the UK to Spain, 1983 and 2003', fontweight='bold', fontsize=14)
    save(fig, 'mock34_task1.png')


def mock41():
    countries = ['Belgium', 'USA', 'Japan', 'Australia']
    fig, axs = plt.subplots(2, 1, figsize=(8.5, 9))
    for ax, title, d00, d70 in [(axs[0], '% men aged 60-64 in employment', [79, 73, 86, 76], [19, 55, 74, 47]),
                                (axs[1], '% women aged 60-64 in employment', [8, 36, 43, 16], [7, 38, 40, 18])]:
        y = np.arange(len(countries))[::-1]
        ax.barh(y + 0.18, d00, 0.36, color='#d9534f', edgecolor='#333', label='2000')
        ax.barh(y - 0.18, d70, 0.36, color='#dbe5f1', edgecolor='#333', hatch='++', label='1970')
        for yy, a, b in zip(y, d00, d70):
            ax.text(a + 1, yy + 0.18, str(a), va='center', fontsize=10)
            ax.text(b + 1, yy - 0.18, str(b), va='center', fontsize=10)
        ax.set_yticks(y)
        ax.set_yticklabels(countries)
        ax.set_xlim(0, 100)
        ax.xaxis.grid(True, color='#ddd')
        ax.set_axisbelow(True)
        ax.set_title(title)
        ax.legend(loc='lower right', frameon=True)
    fig.tight_layout(h_pad=3)
    save(fig, 'mock41_task1.png')


# Mock 55: site watermark; the original shares added up to well over 100% of the economy,
# so the figures are scaled to leave room for other industries (same trends)
def mock55():
    cats = ['Finance', 'Food\nprocessing', 'Manufacturing', 'Tourism', 'Oil, coal\nand gas']
    s = {'2009': [20, 7, 14, 17, 17], '2019': [24, 14, 11, 14, 20], '2029 (forecast)': [27, 7, 4, 14, 17]}
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    grouped_bars(ax, cats, s, ['#404040', '#8c8c8c', '#cfcfcf'])
    ax.set_ylim(0, 30)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v)}%'))
    ax.set_ylabel('Share of the economy')
    ax.set_title("Industries as a percentage of Brazil's economy")
    ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False)
    save(fig, 'mock55_task1.png')


def smooth(xs, ys, n=300):
    xs, ys = np.array(xs, float), np.array(ys, float)
    xn = np.linspace(xs.min(), xs.max(), n)
    # monotone cubic (PCHIP) keeps the curve from overshooting between points
    from scipy.interpolate import PchipInterpolator
    return xn, PchipInterpolator(xs, ys)(xn)


def mock63():
    men = ([1980, 1983, 1985, 1986, 1987, 1990, 1993, 1995, 1997, 1999, 2000, 2001, 2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010],
           [2100, 3300, 3950, 3780, 3820, 3000, 2100, 1700, 1700, 1950, 2700, 3650, 3800, 4200, 5000, 4800, 3700, 2200, 1300, 1000])
    women = ([1980, 1982, 1984, 1986, 1988, 1990, 1992, 1995, 1998, 2001, 2003, 2006, 2008, 2010],
             [1050, 1150, 1500, 1900, 1930, 1950, 2400, 2850, 2550, 2200, 2500, 2850, 2700, 2150])
    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.plot(*smooth(*men), color='#333', lw=2.6, label='men')
    ax.plot(*smooth(*women), color='#333', lw=2.6, ls='--', label='women')
    ax.set_xlim(1980, 2010)
    ax.set_ylim(0, 6000)
    ax.set_xticks(range(1980, 2011, 5))
    ax.yaxis.grid(True, color='#ddd')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v):,}'))
    ax.set_ylabel('Number of members')
    ax.set_title('Gym membership, 1980-2010')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False)
    save(fig, 'mock63_task1.png')


def mock65():
    pet = ([1981, 1983, 1984, 1986, 1987, 1989, 1990, 1991, 1992, 1994, 1996, 1997, 1998, 1999, 2000],
           [90, 118, 137, 139, 137, 110, 100, 99, 104, 134, 140, 143, 140, 144, 147])
    coal = ([1981, 1983, 1984, 1986, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 2000],
            [80, 75, 33, 60, 60, 55, 55, 46, 44, 36, 40, 37, 36])
    gas = ([1981, 1982, 1984, 1986, 1987, 1990, 1991, 1992, 1994, 1995, 1996, 1997, 1998, 1999, 2000],
           [36, 35, 38, 41, 39, 45, 47, 52, 72, 73, 80, 82, 87, 92, 102])
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.plot(*pet, color='#333', ls='--', lw=1.8, label='Petroleum')
    ax.plot(*coal, color='#333', ls='-', lw=1.8, label='Coal')
    ax.plot(*gas, color='#333', ls='-.', lw=1.8, label='Natural gas')
    ax.set_xlim(1981, 2000)
    ax.set_ylim(0, 160)
    ax.set_xticks([1981, 1986, 1991, 1996, 2000])
    ax.yaxis.grid(True, color='#ddd')
    ax.set_ylabel('Million tonnes of oil equivalent')
    ax.set_title('Production levels of the main fuels in the UK between 1981 and 2000')
    ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.1), frameon=False)
    save(fig, 'mock65_task1.png')


if __name__ == '__main__':
    for f in (mock9, mock12, mock29, mock30, mock31, mock32, mock33, mock34, mock41, mock55, mock63, mock65):
        f()
    print('done')
