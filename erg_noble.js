var noble = require('noble');
const readline = require('readline');

function bytesToNumber(bytes) {
	var total=0;
	for (var i=0; i< bytes.length; i++) {
		total += (bytes[i] * Math.pow(256, i));
	}
	return total;
}
function pad(num, size) {

    var s = num+"";
    if(num < 10){
      while (s.length < size) s = "0" + s;
    }
    return s;
}
function secondsToTime(seconds){
  var minutes = Math.floor(seconds/60);
  var remainder = seconds % 60;
  return minutes + ':' + pad(remainder.toFixed(1),4)
}

noble.on('stateChange', function(state) {
  if (state === 'poweredOn') {
    noble.startScanning();
  } else {
    noble.stopScanning();
  }
});


function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function demo() {
  console.log('Taking a break...');
  await sleep(2000);
  console.log('Two seconds later');
  console.log('PM5 430500339 CON')
  console.log('PM5 430500339 MON Speed: 20 Split: 2:12 Stroke Rate: 32')
  console.log('PM5 430500339 MON Distance: 100')
  console.log('PM5 430504875 CON')
  console.log('PM5 430504875 MON Speed: 21 Split: 1:59 Stroke Rate: 35')
  console.log('PM5 430504875 MON Distance: 200')
  console.log('PM5 430503944 CON')
  console.log('PM5 430503944 MON Speed: 22 Split: 1:58 Stroke Rate: 26')
  console.log('PM5 430503944 MON Distance: 400')
  console.log('PM5 430500339 FIN Time: 6:15 Distance: 2000 Avg Split: 1:30.9')
  console.log('PM5 430504875 FIN Time: 6:45 Distance: 2000 Avg Split: 1:35.7')
  console.log('PM5 430500339 FIN Time: 15:0 Distance: 4342 Avg Split: 2:10.2')
  console.log('PM5 430503944 FIN Time: 15:0 Distance: 5345 Avg Split: 2:15.4')
  console.log('PM5 430503944 FIN Time: 6:50 Distance: 2000 Avg Split: 1:36.3')
  console.log('PM5 430503944 MON Speed: 24 Split: 1:59 Stroke Rate: 27')
  console.log('PM5 430503944 MON Distance: 800')
}

demo();






var totalergs = 8
var count = 0
var workoutfinishedcount = 0
noble.on('discover', function(peripheral) {
    //console.log('Found device with local name: ' + peripheral.advertisement.localName);
    //console.log('advertising the following service uuid\'s: ' + peripheral.advertisement.serviceUuids);
    //console.log();
    if(peripheral.advertisement.localName != undefined && peripheral.advertisement.localName.startsWith("PM5")){
      peripheral.connect(function(error) {
        console.log(peripheral.advertisement.localName + ' CON');
        count += 1
        if(count >= totalergs){
          console.log('Stopped Scanning')
          noble.stopScanning();
        }

        peripheral.on('disconnect', function(data) {
              console.log("disconnected")
              console.log(data)
              count -= 1;
              noble.startScanning();
        });

        peripheral.discoverServices(['ce06003043e511e4916c0800200c9a66'], function(error, services) {
          //console.log('discovered the following services:');
          //console.log('  ' + i + ' uuid: ' + services[0].uuid);
          services[0].discoverCharacteristics(['ce06003143e511e4916c0800200c9a66', 'ce06003243e511e4916c0800200c9a66', 'ce06003743e511e4916c0800200c9a66', 'ce06003843e511e4916c0800200c9a66', 'ce06003943e511e4916c0800200c9a66'], function(error, characteristics) {
            var endworkout = characteristics[4];
            var currstroke2 = characteristics[1];
            var currstroke1 = characteristics[0];
            var interval1 = characteristics[2];
            var interval2 = characteristics[3];

            endworkout.on('data', function(data, isNotification) {
              var byteArray = new Uint8Array(data);
              var time = secondsToTime(bytesToNumber([byteArray[4], byteArray[5], byteArray[6]])/100)
              var distance = bytesToNumber([byteArray[7], byteArray[8], byteArray[9]])/10
              var avgsplit = secondsToTime(bytesToNumber([byteArray[18], byteArray[19]])/10)

              if(byteArray[17] != 0 && byteArray[17] != 1 && byteArray[17] != 6 && byteArray[17] != 7 && byteArray[17] != 8 && byteArray[17] != 9){
                console.log(peripheral.advertisement.localName + ' FIN Time: ' + time + ' Distance: ' + distance + ' Avg Split: ' + avgsplit)
              }

            });

            currstroke2.on('data', function(data, isNotification) {
              var byteArray = new Uint8Array(data);
              var curr_speed = (bytesToNumber([byteArray[3], byteArray[4]])/1000).toFixed(2)
              var curr_rate = bytesToNumber([byteArray[5]])
              var curr_split = secondsToTime(bytesToNumber([byteArray[7], byteArray[8]])/100)
              console.log(peripheral.advertisement.localName + ' MON Speed: ' + curr_speed + 'm/s Split: ' + curr_split + ' Stroke Rate: ' + curr_rate)
            });



            currstroke1.on('data', function(data, isNotification) {
              var byteArray = new Uint8Array(data);
              var curr_distance = (bytesToNumber([byteArray[3], byteArray[4], byteArray[5]])/10).toFixed(2)
              console.log(peripheral.advertisement.localName + ' MON Distance: ' + curr_distance)
            });


            interval1.on('data', function(data, isNotification) {
              var byteArray = new Uint8Array(data);
              var time = secondsToTime(bytesToNumber([byteArray[6], byteArray[7], byteArray[8]])/10)
              var distance = bytesToNumber([byteArray[9], byteArray[10], byteArray[11]])
              console.log(peripheral.advertisement.localName + ' FIN Time: ' + time + ' Distance: ' + distance + ' Avg Split: ' + 'N/A')
            });

            // if(forcecurve != undefined){
            //     forcecurve.on('data', function(data, isNotification) {
            //         var byteArray = new Uint8Array(data);
            //         process.stdout.write('force curve ')
            //         var i;
            //         for (i = 0; i < byteArray.length; i++) {
            //             process.stdout.write(byteArray[i] + ' ');
            //         }
            //         console.log('')
            //   });
            // }

            endworkout.subscribe();
            currstroke2.subscribe();
            currstroke1.subscribe();
            interval1.subscribe();
            // forcecurve.subscribe(function(error) {
            //
            // });

        });

        });

      });
    }

});
