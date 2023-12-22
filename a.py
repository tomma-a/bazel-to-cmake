def trans(deps):
    ret=[]
    for i in  deps:
        if i.startswith("@com_google_absl//"):
            ss=i[len("@com_google_absl//"):]
            ii=ss.rfind(":")
            if ii>0:
                ss=ss[ii+1:]
                ret.append("absl::"+ss)
            else:
                ret.append(ss.replace("/","::"))
        else:
            ret.append(i)
    return ret