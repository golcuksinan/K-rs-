import {
useParams
} from "react-router-dom";


import {
useEffect,
useState
} from "react";


import {
getCourse
} from "../../api/courses";


export default function CourseDetail(){


const {id}=useParams();


const [course,setCourse]=useState(null);



useEffect(()=>{


getCourse(id)

.then(res=>{

setCourse(res.data);

});


},[id]);



if(!course){

return <div className="p-20">Yükleniyor...</div>

}



return (

<section className="
max-w-[1200px]
mx-auto
px-6
py-16
">


<h1 className="
heading-font
text-5xl
">

{course.name}

</h1>



<p className="mt-5">

{course.description}

</p>


</section>

);

}