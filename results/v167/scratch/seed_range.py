import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p,a,b=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
ls=open(p,encoding="utf-8").read().splitlines()
print("\n".join("%4d %s"%(i+1,l) for i,l in enumerate(ls[a-1:b])))
