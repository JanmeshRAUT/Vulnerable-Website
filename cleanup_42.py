import os

files = [
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_a.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_a_product.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_b.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_b_product.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_c.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_c_product.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\admin_v2.html",
    r"e:\AS LAb\vulnerable_ecommerce\templates\lab4\sub2_menu.html",
    r"e:\AS LAb\vulnerable_ecommerce\static\css\labs\lab4\sub2_a.css",
    r"e:\AS LAb\vulnerable_ecommerce\static\css\labs\lab4\sub2_b.css",
    r"e:\AS LAb\vulnerable_ecommerce\static\css\labs\lab4\sub2_c.css"
]

for f in files:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted: {f}")
    except Exception as e:
        print(f"Error deleting {f}: {e}")
