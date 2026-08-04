import {
useEffect,
useState
} from "react";


import {
getCurrentUser
} from "../api/users";


import {
AuthContext
} from "./auth-context";



export default function AuthProvider({children}){


const [user,setUser]=useState(null);

// Token yoksa beklenecek bir istek de yok: ilk render'da doğrudan false başlar,
// effect gövdesinde setState çağrılmaz.
const [loading,setLoading]=useState(()=>

Boolean(localStorage.getItem("token"))

);



useEffect(()=>{


const token=localStorage.getItem("token");


if(!token){

return;

}


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