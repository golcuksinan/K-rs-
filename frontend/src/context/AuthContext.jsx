import {
createContext,
useEffect,
useState
} from "react";


import {
getCurrentUser
} from "../api/users";


export const AuthContext=createContext();



export default function AuthProvider({children}){


const [user,setUser]=useState(null);

const [loading,setLoading]=useState(true);



useEffect(()=>{


const token=localStorage.getItem("token");


if(token){


getCurrentUser()

.then(res=>{

setUser(res.data);

})

.catch(()=>{

localStorage.removeItem("token");

})

.finally(()=>{

setLoading(false);

});


}

else{

setLoading(false);

}



},[]);



const login=(data)=>{


localStorage.setItem(

"token",

data.access_token

);


setUser(data.user);


};



const logout=()=>{


localStorage.removeItem("token");

setUser(null);


};



return (

<AuthContext.Provider

value={{

user,

login,

logout,

loading

}}

>


{children}


</AuthContext.Provider>

);


}