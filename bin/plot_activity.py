import bigbang.mailman as mailman
import matplotlib.pyplot as plt

url = "http://mail.scipy.org/pipermail/numpy-discussion/"

dates,broke = mailman.plot_archive(url)

plt.hist([t.toordinal() for t in dates],bins=5000)

plt.show()
