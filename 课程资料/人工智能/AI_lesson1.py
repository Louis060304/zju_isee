import pandas as pd
data = {
    "products" : ["Phone", "Laptop","Pad", "Earphone", "Smart Watch", 
                 "Camera", "Television", "Speaker", "Printer", "Router"],
    "Sales" : [150, 80, 90,200,120, 60,50,130,70,40],
    "Prices($)" : [3000, 6000, 2000, 800, 1500, 5000, 4000, 1500, 1000, 600],
    "Sold Date" : pd.date_range(start="2025-01-01", periods=10, freq='D')
}
df = pd.DataFrame(data)
print(df)